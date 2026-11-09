from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session

from app.models import AuthSession, BehaviorEvent, Bookmark, Content, Order, Reservation, Review, User, WebhookReceipt
from app.core.security import seoul_today


class Store:
    def __init__(self, db: Session):
        self.db = db

    def add(self, obj):
        self.db.add(obj)
        self.db.flush()
        return obj

    def delete(self, obj):
        self.db.delete(obj)

    def rollback(self):
        self.db.rollback()

    def lock_user(self, user_id):
        return self.db.scalar(select(User).where(User.id == user_id).with_for_update())

    def contents_by_ids(self, content_ids):
        return list(self.db.scalars(select(Content).where(Content.id.in_(content_ids)))) if content_ids else []

    def content(self, content_id: int):
        return self.db.get(Content, content_id)

    def user_by_email(self, email: str):
        return self.db.scalar(select(User).where(User.email == email))

    def session(self, digest: str):
        return self.db.get(AuthSession, digest)

    def user(self, user_id: int):
        return self.db.get(User, user_id)

    def update_profile(self, user, values):
        for field, value in values.items():
            setattr(user, field, value)
        self.db.flush()
        return user

    def contents(self, *, q='', category=None, region=None, free_only=False, from_date=None,
                 to_date=None, include_ended=False, sort='latest', page=1, size=24):
        stmt = select(Content)
        if not include_ended:
            stmt = stmt.where(Content.end_date >= seoul_today())
        if q:
            escaped = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            stmt = stmt.where(or_(Content.title.like(f'%{escaped}%', escape='\\'),
                                  Content.venue.like(f'%{escaped}%', escape='\\')))
        if category:
            stmt = stmt.where(Content.category == category)
        if region:
            stmt = stmt.where(Content.region == region)
        if free_only:
            stmt = stmt.where(Content.price == 0, Content.price_text == '무료')
        if from_date:
            stmt = stmt.where(Content.end_date >= from_date)
        if to_date:
            stmt = stmt.where(Content.start_date <= to_date)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        if sort == 'popular':
            counts = select(Bookmark.content_id, func.count().label('count')).group_by(Bookmark.content_id).subquery()
            stmt = stmt.outerjoin(counts, Content.id == counts.c.content_id).order_by(func.coalesce(counts.c.count, 0).desc())
        stmt = stmt.order_by(Content.end_date.asc() if sort == 'ending' else Content.collected_at.desc(), Content.id.asc())
        return list(self.db.scalars(stmt.offset((page - 1) * size).limit(size))), total

    def enrich(self, contents, user_id=None):
        ids = [c.id for c in contents]
        if not ids:
            return {}, set()
        ratings = {cid: (round(float(avg), 1), count) for cid, avg, count in self.db.execute(
            select(Review.content_id, func.avg(Review.rating), func.count()).where(Review.content_id.in_(ids)).group_by(Review.content_id))}
        marked = set(self.db.scalars(select(Bookmark.content_id).where(Bookmark.user_id == user_id, Bookmark.content_id.in_(ids)))) if user_id else set()
        return ratings, marked

    def bookmarks(self, user_id: int):
        return list(self.db.scalars(select(Content).join(Bookmark).where(Bookmark.user_id == user_id).order_by(Bookmark.created_at.desc()).limit(100)))

    def set_bookmark(self, user_id: int, content_id: int, enabled: bool):
        if enabled:
            stmt = insert(Bookmark).values(user_id=user_id, content_id=content_id)
            self.db.execute(stmt.on_duplicate_key_update(content_id=stmt.inserted.content_id))
        else:
            self.db.execute(delete(Bookmark).where(Bookmark.user_id == user_id, Bookmark.content_id == content_id))

    def event(self, values: dict):
        stmt = insert(BehaviorEvent).values(**values)
        self.db.execute(stmt.on_duplicate_key_update(event_id=stmt.inserted.event_id))

    def events(self, user_id: int, limit=500):
        return list(self.db.scalars(select(BehaviorEvent).where(BehaviorEvent.user_id == user_id).order_by(BehaviorEvent.occurred_at.desc()).limit(limit)))

    def recent(self, user_id: int):
        last = select(BehaviorEvent.content_id, func.max(BehaviorEvent.occurred_at).label('last')).where(
            BehaviorEvent.user_id == user_id, BehaviorEvent.event_type == 'content_view').group_by(BehaviorEvent.content_id).subquery()
        return list(self.db.scalars(select(Content).join(last, Content.id == last.c.content_id).order_by(last.c.last.desc()).limit(100)))

    def reviews(self, content_id: int):
        return self.db.execute(select(Review, User.name).join(User, Review.user_id == User.id).where(
            Review.content_id == content_id).order_by(Review.updated_at.desc()).limit(100)).all()

    def review(self, user_id: int, content_id: int):
        return self.db.scalar(select(Review).where(Review.user_id == user_id, Review.content_id == content_id).with_for_update())

    def order(self, payment_id: str, lock=False):
        stmt = select(Order).where(Order.payment_id == payment_id).execution_options(populate_existing=True)
        if lock:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def order_by_key(self, user_id: int, key: str):
        return self.db.scalar(select(Order).where(Order.user_id == user_id, Order.idempotency_key == key).with_for_update())

    def orders(self, user_id: int):
        return list(self.db.scalars(select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()).limit(100)))

    def reservation(self, payment_id: str):
        return self.db.scalar(select(Reservation).where(Reservation.payment_id == payment_id).with_for_update())

    def reservations(self, user_id: int):
        return self.db.execute(select(Reservation, Content, Order).join(Content, Reservation.content_id == Content.id).join(
            Order, Reservation.payment_id == Order.payment_id).where(Reservation.user_id == user_id).order_by(Reservation.created_at.desc()).limit(100)).all()

    def receipt(self, event_id: str):
        return self.db.get(WebhookReceipt, event_id)

    def source_content(self, source: str, source_id: str):
        return self.db.scalar(select(Content).where(Content.source == source, Content.source_id == source_id))
