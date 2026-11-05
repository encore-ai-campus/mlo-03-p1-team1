"""Import a Naver exhibition CSV into the existing contents table and poster directory."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import date
import hashlib
from html import unescape
import json
from pathlib import Path
import time

import httpx
from sqlalchemy import inspect, select
from sqlalchemy.dialects.mysql import insert

from app.core.security import utcnow
from app.db.session import engine
from app.models import Content
from app.pipelines.normalize import safe_url


ROOT = Path(__file__).resolve().parents[3]
SOURCE = 'naver_exhibitions'
MAX_POSTER_BYTES = 10 * 1024 * 1024
REGIONS = {
    '서울': '서울', '부산': '부산', '대구': '대구', '인천': '인천',
    '광주': '광주', '대전': '대전', '울산': '울산', '세종': '세종',
    '경기': '경기', '강원': '강원', '충청북': '충북', '충청남': '충남',
    '전라북': '전북', '전북': '전북', '전라남': '전남', '경상북': '경북',
    '경상남': '경남', '제주': '제주',
}


def csv_text(value: str, length: int) -> str:
    # These CSV fields are plain text: preserve '&' and angle brackets in names.
    return ' '.join(unescape(value or '').split())[:length]


def identity(row: dict) -> str:
    # CSV ranks/pages change between exports; event and venue identify a record.
    parts = [row.get(key, '').strip() for key in ('title', 'venue', 'naver_map_pin_id')]
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode('utf-8')).hexdigest()


def normalize_row(row: dict, image_url: str) -> dict:
    title, venue = csv_text(row.get('title', ''), 300), csv_text(row.get('venue', ''), 200)
    if not title or not venue:
        raise ValueError('missing_title_or_venue')
    if not row.get('start_date', '').strip() or not row.get('end_date', '').strip():
        raise ValueError('missing_dates')
    try:
        start, end = (date.fromisoformat(row[key].strip()) for key in ('start_date', 'end_date'))
    except ValueError as exc:
        raise ValueError('invalid_dates') from exc
    if end < start:
        raise ValueError('reversed_dates')
    address = csv_text(row.get('road_address', ''), 400)
    region = next((short for full, short in REGIONS.items() if address.startswith(full)), '지역 확인 필요')
    description = [f'{title}\n장소: {venue}', '전시 일정·관람료와 상세 정보는 주최 기관에서 확인해 주세요.']
    if row.get('snapshot_date'):
        description.append(f"네이버 검색 수집 기준일: {csv_text(row['snapshot_date'], 30)}")
    map_url = safe_url(row.get('naver_map_url', ''))
    if map_url:
        description.append(f'장소 지도: {map_url}')
    return dict(
        source=SOURCE, source_id=identity(row), title=title, subtitle='', category='전시',
        region=region, venue=venue, address=address, start_date=start, end_date=end,
        price=0, price_text='주최 기관 확인', description='\n\n'.join(description),
        image_url=image_url, source_url=safe_url(row.get('source_url', '')),
        tags=['전시'], is_sample=False, bookable=False,
    )


def image_extension(data: bytes) -> str:
    if data.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    if data.startswith((b'GIF87a', b'GIF89a')):
        return '.gif'
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return '.webp'
    raise ValueError('unsupported_or_invalid_image')


def download_poster(client: httpx.Client, row: dict, directory: Path) -> dict:
    key = identity(row)
    url = safe_url(row.get('poster_source_url', ''))
    result = {'source_id': key, 'rank': row.get('rank'), 'image_url': '/posters/fallback.svg'}
    if not url:
        return {**result, 'status': 'missing_url'}
    for extension in ('.jpg', '.png', '.gif', '.webp'):
        cached = directory / f'naver-{key}{extension}'
        if cached.is_file():
            try:
                data = cached.read_bytes()
                if len(data) <= MAX_POSTER_BYTES and image_extension(data) == extension:
                    return {**result, 'status': 'cached', 'image_url': f'/posters/{cached.name}'}
            except ValueError:
                pass
    for attempt in range(3):
        try:
            with client.stream('GET', url) as response:
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_POSTER_BYTES:
                        raise ValueError('image_too_large')
            extension = image_extension(body)
            destination = directory / f'naver-{key}{extension}'
            temporary = destination.with_suffix(extension + '.part')
            temporary.write_bytes(body)
            temporary.replace(destination)
            return {**result, 'status': 'downloaded', 'bytes': len(body), 'image_url': f'/posters/{destination.name}'}
        except (httpx.HTTPError, ValueError) as exc:
            failure = type(exc).__name__
            if attempt < 2:
                time.sleep(attempt + 1)
    return {**result, 'status': 'failed', 'error': failure}


def run(csv_path: Path, poster_dir: Path, report_path: Path, workers: int = 8, dry_run: bool = False) -> dict:
    with csv_path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        required = {'title', 'venue', 'start_date', 'end_date', 'poster_source_url'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('CSV is missing required columns')
        rows = list(reader)
    if not rows:
        raise ValueError('CSV contains no records')
    keys = [identity(row) for row in rows]
    if len(set(keys)) != len(keys):
        raise ValueError('CSV contains duplicate event identities; review before importing')
    # Validate access and the actual table before downloading or writing anything.
    with engine.connect() as connection:
        if connection.dialect.name not in ('mysql', 'mariadb'):
            raise ValueError('MariaDB is required')
        columns = {column['name'] for column in inspect(connection).get_columns('contents')}
        if not set(Content.__table__.columns.keys()).issubset(columns):
            raise ValueError('Existing contents schema differs from the application; inspect migrations')
        existing = set(connection.execute(select(Content.source_id).where(Content.source == SOURCE)).scalars())

    valid, skipped = [], []
    for row in rows:
        try:
            valid.append(normalize_row(row, '/posters/fallback.svg'))
        except ValueError as exc:
            skipped.append({'reason': str(exc), 'row': row})
    summary = dict(csv_rows=len(rows), importable=len(valid), inserted=0, updated=0, skipped=len(skipped),
                   downloaded=0, cached=0, missing_poster_url=0, failed_posters=0, dry_run=dry_run)
    report = {'database': {'host': engine.url.host, 'port': engine.url.port, 'name': engine.url.database},
              'csv_path': str(csv_path.resolve()), 'summary': summary, 'skipped': skipped,
              'posters': [], 'source_rows': rows}
    if dry_run:
        print(json.dumps(summary), flush=True)
        return report
    if not poster_dir.is_dir():
        raise ValueError('Use the existing frontend/public/posters directory')

    print(f'CSV: {len(rows)} rows; {len(valid)} importable; {len(skipped)} skipped.', flush=True)
    print(f'Downloading posters into {poster_dir} (existing files are reused).', flush=True)
    with httpx.Client(timeout=20, follow_redirects=True,
                      limits=httpx.Limits(max_connections=workers, max_keepalive_connections=workers),
                      headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://search.naver.com/'}) as client:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(download_poster, client, row, poster_dir) for row in rows]
            for future in as_completed(futures):
                report['posters'].append(future.result())
                if len(report['posters']) % 50 == 0 or len(report['posters']) == len(rows):
                    print(f"Posters: {len(report['posters'])}/{len(rows)} processed.", flush=True)
    for poster in report['posters']:
        field = {'downloaded': 'downloaded', 'cached': 'cached', 'missing_url': 'missing_poster_url', 'failed': 'failed_posters'}[poster['status']]
        summary[field] += 1
    posters = {poster['source_id']: poster for poster in report['posters']}
    # A failed download can be retried without committing any partial catalogue.
    if summary['failed_posters']:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        raise RuntimeError(f"{summary['failed_posters']} poster downloads failed; database was not changed. See {report_path}")
    now = utcnow()
    for values in valid:
        values['image_url'] = posters[values['source_id']]['image_url']
        values['collected_at'] = now
        summary['updated' if values['source_id'] in existing else 'inserted'] += 1
    # Preserve unrelated data, content IDs, bookmarks and reviews when reimporting.
    with engine.begin() as connection:
        for values in valid:
            statement = insert(Content).values(**values)
            mutable = {key: statement.inserted[key] for key in values
                       if key not in ('source', 'source_id', 'collected_at', 'bookable', 'price', 'price_text')}
            connection.execute(statement.on_duplicate_key_update(**mutable))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary), flush=True)
    print(f'Report (includes skipped source rows): {report_path}', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_path', type=Path)
    parser.add_argument('--poster-dir', type=Path, default=ROOT / 'frontend/public/posters')
    parser.add_argument('--report', type=Path, default=ROOT / '.runtime/naver-import-report.json')
    parser.add_argument('--workers', type=int, choices=range(1, 17), default=8)
    parser.add_argument('--dry-run', action='store_true', help='Validate CSV and DB schema without changing data or downloading.')
    arguments = parser.parse_args()
    try:
        run(arguments.csv_path, arguments.poster_dir, arguments.report, arguments.workers, arguments.dry_run)
    except Exception as exc:
        # Driver/HTTP error messages may contain credentials or entire source URLs.
        print(f'Import failed ({type(exc).__name__}). Check DB access, CSV dates, poster access and the report.', flush=True)
        raise SystemExit(1)
    finally:
        engine.dispose()
