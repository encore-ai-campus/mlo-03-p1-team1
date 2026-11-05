"""Import Culture Portal dataset 580 into the existing MariaDB contents table."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

import httpx
from sqlalchemy import inspect, select, text
from sqlalchemy.dialects.mysql import insert

from app.collectors.culture_portal import KcisaCulturePortal
from app.core.config import get_settings
from app.core.security import seoul_today, utcnow
from app.db.session import engine
from app.models import Content
from app.pipelines.normalize import normalize_kcisa
from app.tasks.import_naver import image_extension


ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / '.runtime/culture-kcisa-raw.json'
REPORT = ROOT / '.runtime/culture-kcisa-import-report.json'


def fetch_snapshot(destination=SNAPSHOT, genre_records=None):
    def progress(genre, page, count, total):
        print(f'KCISA {genre}: page {page}, {count} records (reported global total {total}).', flush=True)
    if genre_records is None:
        genre_records = list(KcisaCulturePortal(get_settings()).collect(progress))
    genres = {row.get('url'): row['_dtype'] for row in genre_records if row.get('url')}
    # Some records are not assigned to any documented dtype. Include the global list too.
    portal = KcisaCulturePortal(get_settings())
    portal.GENRES = ('',)
    records = list(portal.collect(progress))
    for row in records:
        row['_dtype'] = genres.get(row.get('url'), '기타')
        row['_genre_verified'] = row.get('url') in genres
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({'fetched_at': datetime.now().isoformat(), 'records': records}, ensure_ascii=False), encoding='utf-8')
    print(f'Saved {len(records)} source records to {destination}.', flush=True)
    return records


def poster(client, values):
    key = hashlib.sha256(values['source_id'].encode()).hexdigest()
    directory = ROOT / 'frontend/public/posters'
    for extension in ('.jpg', '.png', '.gif', '.webp'):
        path = directory / f'kcisa-{key}{extension}'
        if path.is_file():
            try:
                if image_extension(path.read_bytes()) == extension:
                    return values['source_id'], f'/posters/{path.name}', 'cached'
            except ValueError:
                pass
    if not values['image_url']:
        return values['source_id'], '/posters/fallback.svg', 'missing_url'
    for _ in range(2):
        try:
            with client.stream('GET', values['image_url']) as response:
                response.raise_for_status()
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 10 * 1024 * 1024:
                        raise ValueError('Image too large')
            extension = image_extension(data)
            path = directory / f'kcisa-{key}{extension}'
            temporary = path.with_suffix(extension + '.part')
            temporary.write_bytes(data)
            temporary.replace(path)
            return values['source_id'], f'/posters/{path.name}', 'downloaded'
        except (httpx.HTTPError, ValueError):
            pass
    return values['source_id'], '/posters/fallback.svg', 'failed'


def run(records, demo_attributes=False, dry_run=False, report_path=REPORT):
    today = seoul_today()
    values_by_id, audit_by_id, skipped = {}, {}, []
    for raw in records:
        try:
            values, audit = normalize_kcisa(raw, today, demo_attributes)
            values['description'] = values['description'].encode('utf-8')[:60000].decode('utf-8', errors='ignore')
            values_by_id[values['source_id']], audit_by_id[values['source_id']] = values, audit
        except ValueError as exc:
            skipped.append({'reason': str(exc), 'row': raw})
    if not values_by_id:
        raise ValueError('No valid source records')
    values = sorted(values_by_id.values(), key=lambda row: int(row['source_id']) if row['source_id'].isdigit() else 0, reverse=True)
    active = [row for row in values if row['end_date'] >= today]
    with engine.connect() as connection:
        columns = {column['name'] for column in inspect(connection).get_columns('contents')}
        if not set(Content.__table__.columns.keys()).issubset(columns):
            raise ValueError('Existing contents schema differs from application')
        if connection.execute(text('SELECT @@read_only')).scalar():
            raise ValueError('Write to the master database, not a replica')
        existing = set(connection.execute(select(Content.source_id).where(Content.source == 'culture_kcisa')).scalars())
        before_sources = dict(connection.execute(text('SELECT source, COUNT(*) FROM contents GROUP BY source')).all())
    summary = {
        'source_rows': len(records), 'unique_valid': len(values), 'skipped': len(skipped),
        'duplicates_merged': len(records) - len(skipped) - len(values),
        'inserted': len(set(values_by_id) - existing), 'updated': len(set(values_by_id) & existing),
        'date_adjusted': sum(audit['date_adjusted'] for audit in audit_by_id.values()),
        'active_or_upcoming': len(active), 'demo_attributes': demo_attributes,
        'active_categories': dict(Counter(row['category'] for row in active)),
        'active_regions': dict(Counter(row['region'] for row in active)),
        'active_prices': dict(Counter(row['price'] for row in active)),
        'posters': {}, 'committed': False,
    }
    report = {
        'database': {'host': engine.url.host, 'port': engine.url.port, 'name': engine.url.database},
        'as_of': today.isoformat(), 'summary': summary, 'existing_sources_before': before_sources,
        'normalization_audit': list(audit_by_id.values()), 'skipped': skipped, 'poster_results': [],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if dry_run:
        return report
    if not (ROOT / 'frontend/public/posters').is_dir():
        raise ValueError('Existing poster directory is required')
    # Only currently visible items need local images; archived items retain source URLs.
    with httpx.Client(timeout=15, follow_redirects=True,
                      headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.culture.go.kr/'},
                      limits=httpx.Limits(max_connections=8, max_keepalive_connections=8)) as client:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(poster, client, row) for row in active]
            for count, future in enumerate(as_completed(futures), 1):
                source_id, image_url, status = future.result()
                values_by_id[source_id]['image_url'] = image_url
                report['poster_results'].append({'source_id': source_id, 'status': status, 'image_url': image_url})
                if count % 100 == 0 or count == len(active):
                    print(f'Posters: {count}/{len(active)} processed.', flush=True)
    summary['posters'] = dict(Counter(item['status'] for item in report['poster_results']))
    now = utcnow().replace(microsecond=0)
    for row in values:
        row['collected_at'] = now
    statement = insert(Content)
    updates = {key: statement.inserted[key] for key in values[0] if key not in ('source', 'source_id', 'collected_at')}
    # No DDL or deletion: existing content IDs, users, bookmarks and other sources survive.
    with engine.begin() as connection:
        for offset in range(0, len(values), 200):
            connection.execute(statement.on_duplicate_key_update(**updates), values[offset:offset + 200])
            if offset % 5000 == 0:
                print(f'DB batch: {min(offset + 200, len(values))}/{len(values)} staged in transaction.', flush=True)
    summary['committed'] = True
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Import committed: ' + json.dumps(summary, ensure_ascii=False), flush=True)
    print(f'Report: {report_path}', flush=True)
    return report


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch-only', action='store_true')
    parser.add_argument('--from-snapshot', type=Path)
    parser.add_argument('--demo-attributes', action='store_true', help='Use user-authorized synthetic regions/prices and mark records as samples.')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--report', type=Path, default=REPORT)
    args = parser.parse_args()
    try:
        if args.fetch_only:
            fetch_snapshot()
        else:
            records = json.loads(args.from_snapshot.read_text(encoding='utf-8'))['records'] if args.from_snapshot else fetch_snapshot()
            run(records, args.demo_attributes, args.dry_run, args.report)
    except Exception as exc:
        print(f'Import failed ({type(exc).__name__}). Check configuration and the report; no partial DB batch was committed.', flush=True)
        raise SystemExit(1)
    finally:
        engine.dispose()
