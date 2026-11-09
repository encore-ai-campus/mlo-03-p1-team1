import asyncio
import json
import socket
from datetime import timedelta, timezone
import logging

from sqlalchemy import select

from app.core.security import utcnow
from app.db.session import SessionLocal
from app.models import BehaviorEvent, EventOutbox, Review, User
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


def log_active_user_snapshot(bucket_start):
    bucket_end = bucket_start + timedelta(minutes=1)
    stmt = select(BehaviorEvent.event_id, BehaviorEvent.user_id, User.name, BehaviorEvent.properties).outerjoin(
        User, User.id == BehaviorEvent.user_id
    ).where(BehaviorEvent.occurred_at >= bucket_start, BehaviorEvent.occurred_at < bucket_end)
    with SessionLocal() as db:
        rows = db.execute(stmt).all()
        review_rows = db.execute(
            select(Review.user_id, User.name).join(User, User.id == Review.user_id).where(
                Review.updated_at >= bucket_start, Review.updated_at < bucket_end
            )
        ).all()

    actors = {}
    anonymous = set()
    for event_id, user_id, user_name, properties in rows:
        if user_id is not None:
            actors[f'user:{user_id}'] = user_name or '이름 없음'
            continue
        context = (properties or {}).get('_context') or {}
        anonymous_id = context.get('anonymous_id') or context.get('session_id')
        anonymous.add(str(anonymous_id or event_id))
    for user_id, user_name in review_rows:
        actors[f'user:{user_id}'] = user_name or '이름 없음'

    names = sorted(actors.values())
    if anonymous:
        names.append(f'비회원 {len(anonymous)}명')
    record = {
        'log_type': 'active_users_minute',
        'bucket_start': bucket_start.replace(tzinfo=timezone.utc).isoformat(),
        'bucket_end': bucket_end.replace(tzinfo=timezone.utc).isoformat(),
        'active_user_count': len(actors) + len(anonymous),
        'active_user_names': names,
        'active_user_names_text': ', '.join(names) if names else 'none',
    }
    logger.info('ODDINARY_ACTIVE_USERS %s', json.dumps(record, separators=(',', ':'), ensure_ascii=False))


async def event_delivery_loop(stop):
    last_snapshot_bucket = None
    snapshot_enabled = socket.gethostname() == 'fastapi1'
    while not stop.is_set():
        try:
            await asyncio.to_thread(dispatch_batch)
        except Exception as exc:
            logger.warning('Event outbox poll failed (%s)', type(exc).__name__)
        current_bucket = utcnow().replace(second=0, microsecond=0)
        if snapshot_enabled and current_bucket != last_snapshot_bucket:
            last_snapshot_bucket = current_bucket
            try:
                await asyncio.to_thread(log_active_user_snapshot, current_bucket - timedelta(minutes=1))
            except Exception as exc:
                logger.warning('Active user snapshot failed (%s)', type(exc).__name__)
        try:
            await asyncio.wait_for(stop.wait(), timeout=1)
        except TimeoutError:
            pass
