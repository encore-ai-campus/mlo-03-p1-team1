import asyncio
from datetime import timedelta
import logging

from sqlalchemy import select

from app.core.security import utcnow
from app.db.session import SessionLocal
from app.models import BehaviorEvent, EventOutbox
from app.repositories.events import deliver

logger = logging.getLogger('culturepick.events')


def dispatch_batch(limit=25):
    completed = 0
    for _ in range(limit):
        with SessionLocal.begin() as db:
            pending = db.scalar(select(EventOutbox).where(
                EventOutbox.delivered_at.is_(None), EventOutbox.next_attempt_at <= utcnow()
            ).order_by(EventOutbox.next_attempt_at, EventOutbox.event_id).limit(1).with_for_update(skip_locked=True))
            if pending is None:
                break
            pending.attempts += 1
            try:
                deliver(db.get(BehaviorEvent, pending.event_id))
            except Exception as exc:
                # Exception text can include a DB URI: retain only the class name.
                pending.last_error = type(exc).__name__[:80]
                pending.next_attempt_at = utcnow() + timedelta(seconds=min(300, 2 ** min(pending.attempts, 9)))
                logger.warning('Mongo event delivery deferred (%s)', pending.last_error)
                break
            pending.delivered_at = utcnow()
            pending.last_error = None
            completed += 1
    return completed


async def event_delivery_loop(stop):
    while not stop.is_set():
        try:
            await asyncio.to_thread(dispatch_batch)
        except Exception as exc:
            logger.warning('Event outbox poll failed (%s)', type(exc).__name__)
        try:
            await asyncio.wait_for(stop.wait(), timeout=1)
        except TimeoutError:
            pass
