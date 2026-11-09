from datetime import date, datetime

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import utcnow
from app.db.base import Base


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(40))
    password_hash: Mapped[str] = mapped_column(String(256))
    categories: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    survey_completed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    @property
    def is_admin(self):
        from app.core.config import get_settings
        return self.email.casefold() in {e.casefold() for e in get_settings().admin_emails}


class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class Content(Base):
    __tablename__ = 'contents'
    __table_args__ = (UniqueConstraint('source', 'source_id', name='uq_content_source'),
                      Index('ix_contents_category_end', 'category', 'end_date'),
                      CheckConstraint('price >= 0', name='ck_content_price'))
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(30))
    source_id: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(300))
    subtitle: Mapped[str] = mapped_column(String(300), default='')
    category: Mapped[str] = mapped_column(String(20))
    region: Mapped[str] = mapped_column(String(30))
    venue: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(400), default='')
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    price: Mapped[int] = mapped_column(default=0)
    price_text: Mapped[str] = mapped_column(String(200), default='')
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(1000), default='')
    source_url: Mapped[str] = mapped_column(String(1000), default='')
    tags: Mapped[list] = mapped_column(JSON, default=list)
    is_sample: Mapped[bool] = mapped_column(default=False)
    bookable: Mapped[bool] = mapped_column(default=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Bookmark(Base):
    __tablename__ = 'bookmarks'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey('contents.id', ondelete='CASCADE'), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Review(Base):
    __tablename__ = 'reviews'
    __table_args__ = (UniqueConstraint('user_id', 'content_id', name='uq_review_user_content'),
                      CheckConstraint('rating BETWEEN 1 AND 5', name='ck_review_rating'))
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    content_id: Mapped[int] = mapped_column(ForeignKey('contents.id', ondelete='CASCADE'), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class BehaviorEvent(Base):
    __tablename__ = 'behavior_events'
    __table_args__ = (Index('ix_events_user_time', 'user_id', 'occurred_at'),)
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(40))
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    content_id: Mapped[int | None] = mapped_column(ForeignKey('contents.id', ondelete='SET NULL'), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)


class Order(Base):
    __tablename__ = 'orders'
    __table_args__ = (UniqueConstraint('user_id', 'idempotency_key', name='uq_order_idempotency'),
                      CheckConstraint('amount > 0 AND quantity BETWEEN 1 AND 4', name='ck_order_amount'))
    payment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    content_id: Mapped[int] = mapped_column(ForeignKey('contents.id'))
    idempotency_key: Mapped[str] = mapped_column(String(36))
    order_name: Mapped[str] = mapped_column(String(300))
    quantity: Mapped[int] = mapped_column(default=1)
    amount: Mapped[int] = mapped_column()
    cancelled_amount: Mapped[int] = mapped_column(default=0, server_default='0')
    currency: Mapped[str] = mapped_column(String(10), default='KRW')
    status: Mapped[str] = mapped_column(String(30), default='PENDING')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PaymentHistory(Base):
    __tablename__ = 'payment_history'
    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[str] = mapped_column(ForeignKey('orders.payment_id'), index=True)
    status: Mapped[str] = mapped_column(String(30))
    amount: Mapped[int] = mapped_column()
    cancelled_amount: Mapped[int] = mapped_column(default=0, server_default='0')
    provider_transaction_id: Mapped[str] = mapped_column(String(200), default='', server_default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Reservation(Base):
    __tablename__ = 'reservations'
    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[str] = mapped_column(ForeignKey('orders.payment_id'), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    content_id: Mapped[int] = mapped_column(ForeignKey('contents.id'))
    status: Mapped[str] = mapped_column(String(30), default='CONFIRMED')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class WebhookReceipt(Base):
    __tablename__ = 'webhook_receipts'
    event_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    payment_id: Mapped[str] = mapped_column(String(64))
    received_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Visit(Base):
    __tablename__ = 'visits'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey('contents.id', ondelete='CASCADE'), primary_key=True)
    visited_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CollectionRun(Base):
    __tablename__ = 'collection_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='RUNNING')
    collected_count: Mapped[int] = mapped_column(default=0)
    error_code: Mapped[str] = mapped_column(String(100), default='')
