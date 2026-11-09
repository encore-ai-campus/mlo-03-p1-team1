from uuid import uuid4

from fastapi import HTTPException

from app.core.security import seoul_today, utcnow
from app.models import Order, PaymentHistory, Reservation
from app.services.catalog import CatalogService


class SimulatedPaymentService:
    """Records a purchase decision without contacting a payment provider."""

    def __init__(self, store):
        self.store = store

    def owned(self, payment_id, user):
        order = self.store.order(payment_id)
        if order is None or order.user_id != user.id:
            raise HTTPException(404, '주문을 찾을 수 없습니다.')
        return order

    def complete(self, user, data, key):
        # Serialize the user's retries, including concurrent first requests.
        self.store.lock_user(user.id)
        existing = self.store.order_by_key(user.id, str(key))
        if existing:
            if (not existing.is_simulated or existing.status != 'PAID'
                    or (existing.content_id, existing.quantity) != (data.content_id, data.quantity)):
                raise HTTPException(409, '같은 요청 키로 다른 결제를 처리할 수 없습니다.')
            return existing

        content = CatalogService(self.store).require(data.content_id)
        if content.price <= 0:
            raise HTTPException(403, '금액이 등록된 유료 콘텐츠만 결제할 수 있습니다.')
        if content.end_date < seoul_today():
            raise HTTPException(409, '종료된 콘텐츠는 결제할 수 없습니다.')
        amount = content.price * data.quantity
        if amount > 2_147_483_647:
            raise HTTPException(422, '결제 가능한 금액을 초과했습니다.')

        # MariaDB DATETIME uses whole seconds; retries must return the same snapshot.
        now = utcnow().replace(microsecond=0)
        order = self.store.add(Order(
            payment_id=f'sim-{uuid4()}', user_id=user.id, content_id=content.id,
            idempotency_key=str(key), order_name=content.title, quantity=data.quantity,
            amount=amount, currency='KRW', status='PAID', created_at=now, updated_at=now,
        ))
        self.store.add(PaymentHistory(
            payment_id=order.payment_id, status='PAID', amount=amount,
            cancelled_amount=0, provider_transaction_id='simulation',
        ))
        self.store.add(Reservation(
            payment_id=order.payment_id, user_id=user.id, content_id=content.id,
            status='CONFIRMED',
        ))
        self.store.event({
            'event_id': str(uuid4()), 'event_type': 'payment_completed',
            'user_id': user.id, 'content_id': content.id,
            'properties': {'payment_id': order.payment_id, 'payment_mode': 'simulation',
                           'quantity': order.quantity, 'amount': amount, 'currency': 'KRW'},
        })
        # get_db commits all four records together; any failure rolls them all back.
        return order
