"""Report delivery state without exposing connection strings or event payloads."""
import json
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.db.mongo import user_events, close_mongo
from app.models import EventOutbox


if __name__ == '__main__':
    with SessionLocal() as db:
        total = db.scalar(select(func.count()).select_from(EventOutbox))
        pending = db.scalar(select(func.count()).select_from(EventOutbox).where(EventOutbox.delivered_at.is_(None)))
        errors = list(db.scalars(select(EventOutbox.last_error).where(EventOutbox.last_error.is_not(None)).distinct()))
    try:
        mongo_count = user_events().count_documents({})
        print(json.dumps({'outbox_total': total, 'pending': pending, 'delivered': total - pending,
                          'error_classes': errors, 'mongo_documents': mongo_count}))
    finally:
        close_mongo()
