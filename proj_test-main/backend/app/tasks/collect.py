import argparse
from datetime import timedelta
import logging
import time

from app.collectors.culture_portal import CollectionError, CulturePortal
from app.core.config import get_settings
from app.core.security import seoul_today, utcnow
from app.db.session import SessionLocal
from app.models import CollectionRun, Content
from app.pipelines.normalize import normalize
from app.repositories.store import Store


def _collect(days=90, pages=5):
    count = 0
    # A failed upstream fetch rolls back this batch; existing data stays available.
    with SessionLocal.begin() as db:
        store = Store(db)
        for raw in CulturePortal(get_settings()).collect(seoul_today(), seoul_today() + timedelta(days=days), pages):
            try:
                values = normalize(raw)
            except ValueError:
                logging.warning('Skipped invalid culture record (missing identity/date).')
                continue
            content = store.source_content(values['source'], values['source_id'])
            if content:
                for key, value in values.items():
                    setattr(content, key, value)
                content.collected_at = utcnow()
            else:
                store.add(Content(**values))
            count += 1
    logging.info('Collected %s culture records.', count)
    return count


def collect(days=90, pages=5):
    with SessionLocal.begin() as db:
        run = CollectionRun(status='RUNNING', collected_count=0, error_code='')
        db.add(run)
        db.flush()
        run_id = run.id
    try:
        count = _collect(days, pages)
    except Exception as exc:
        with SessionLocal.begin() as db:
            run = db.get(CollectionRun, run_id)
            run.status, run.error_code, run.finished_at = 'FAILED', type(exc).__name__, utcnow()
        raise
    with SessionLocal.begin() as db:
        run = db.get(CollectionRun, run_id)
        run.status, run.collected_count, run.finished_at = 'SUCCESS', count, utcnow()
    return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=90)
    parser.add_argument('--pages', type=int, default=5)
    parser.add_argument('--interval', type=int, default=0, help='Repeat every N seconds; 0 runs once.')
    args = parser.parse_args()
    if not 1 <= args.days <= 365 or not 1 <= args.pages <= 100 or args.interval < 0:
        parser.error('days 1..365, pages 1..100, interval >= 0 required')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    while True:
        try:
            collect(args.days, args.pages)
        except Exception as exc:
            logging.error('Collection failed (%s). Check configuration; existing data preserved.', type(exc).__name__)
            if not args.interval:
                raise SystemExit(1)
        if not args.interval:
            break
        time.sleep(max(args.interval, 60))
