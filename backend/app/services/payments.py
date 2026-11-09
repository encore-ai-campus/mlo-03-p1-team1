import json
from uuid import uuid4

from fastapi import HTTPException

from app.core.security import seoul_today, utcnow
from app.models import Order, PaymentHistory, Reservation, WebhookReceipt
from app.services.catalog import CatalogService


class PaymentService:
    def __init__(self, store, settings, provider):
        self.store, self.settings, self.provider = store, settings, provider

    def require_ready(self):
        if not self.settings.payment_ready:
            raise HTTPException(503, '결제 준비 중입니다. 상점·PG 채널 및 서버 키 설정이 필요합니다.')

    def create_order(self, user, data, key):
        self.require_ready()
        # Serializes order-key creation per user; uniqueness is also enforced in MariaDB.
        self.store.lock_user(user.id)
        existing = self.store.order_by_key(user.id, str(key))
        if existing:
            if (existing.content_id, existing.quantity) != (data.content_id, data.quantity):
                raise HTTPException(409, '같은 요청 키로 다른 주문을 생성할 수 없습니다.')
            return existing
        content = CatalogService(self.store).require(data.content_id)
        if content.is_sample or not content.bookable or content.price <= 0:
            raise HTTPException(403, '이 콘텐츠는 서비스 내 결제를 지원하지 않습니다.')
        if content.start_date <= seoul_today():
            raise HTTPException(409, '판매 가능 기간이 아닙니다.')
        return self.store.add(Order(payment_id=f'cp-{uuid4()}', user_id=user.id, content_id=content.id,
                                    idempotency_key=str(key), order_name=content.title, quantity=data.quantity,
                                    amount=content.price * data.quantity))

    def owned(self, payment_id, user, lock=False):
        order = self.store.order(payment_id, lock=lock)
        if order is None or (user is not None and order.user_id != user.id):
            raise HTTPException(404, '주문을 찾을 수 없습니다.')
        return order

    def sync(self, order):
        payment = self.provider.get_payment(order.payment_id)
        status = payment.get('status')
        if payment.get('id') != order.payment_id or payment.get('storeId') != self.settings.portone_store_id:
            raise HTTPException(409, '결제와 주문의 대응 관계가 일치하지 않습니다.')
        if status not in ('PAID', 'CANCELLED', 'PARTIAL_CANCELLED'):
            return order
        try:
            custom = payment.get('customData', '{}')
            custom = json.loads(custom) if isinstance(custom, str) else custom
            amounts = payment.get('amount', {})
            cancelled = amounts.get('cancelled', 0)
            valid = (isinstance(custom, dict) and custom.get('order_id') == order.payment_id
                     and type(amounts.get('total')) is int and amounts['total'] == order.amount
                     and type(cancelled) is int and 0 <= cancelled <= order.amount
                     and payment.get('currency') == order.currency)
            valid = valid and ((status == 'PAID' and cancelled == 0) or
                               (status == 'CANCELLED' and cancelled == order.amount) or
                               (status == 'PARTIAL_CANCELLED' and 0 < cancelled < order.amount))
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise HTTPException(409, '결제 금액·통화·주문 정보가 일치하지 않습니다.')
        # Never regress a cancelled payment from an old/out-of-order response.
        if order.status == 'CANCELLED':
            return order
        if order.status == 'PARTIAL_CANCELLED' and status == 'PAID':
            return order
        if cancelled < order.cancelled_amount:
            return order
        target = status
        reservation = self.store.reservation(order.payment_id)
        if target == 'PAID' and reservation is None:
            self.store.add(Reservation(payment_id=order.payment_id, user_id=order.user_id, content_id=order.content_id))
        elif reservation and target in ('CANCELLED', 'PARTIAL_CANCELLED'):
            reservation.status = 'CANCELLED' if target == 'CANCELLED' else 'REVIEW_REQUIRED'
        if order.status != target or order.cancelled_amount != cancelled:
            order.status = target
            order.cancelled_amount = cancelled
            order.updated_at = utcnow()
            self.store.add(PaymentHistory(payment_id=order.payment_id, status=target, amount=order.amount,
                                           cancelled_amount=cancelled,
                                           provider_transaction_id=str(payment.get('transactionId', ''))[:200]))
            self.store.event({
                'event_id': str(uuid4()),
                'event_type': 'payment_completed' if target == 'PAID' else 'payment_cancelled',
                'user_id': order.user_id, 'content_id': order.content_id,
                'properties': {'payment_id': order.payment_id, 'payment_mode': 'portone_v2',
                               'quantity': order.quantity, 'amount': order.amount,
                               'currency': order.currency, 'cancelled_amount': cancelled},
            })
        return order

    def verify(self, payment_id, user):
        self.require_ready()
        return self.sync(self.owned(payment_id, user, lock=True))

    def cancel(self, payment_id, user, reason):
        self.require_ready()
        if not self.settings.refunds_enabled:
            raise HTTPException(403, '취소·환불 정책 확정 후 이용할 수 있습니다.')
        order = self.owned(payment_id, user, lock=True)
        self.sync(order)
        if order.status == 'CANCELLED':
            return order
        content = CatalogService(self.store).require(order.content_id)
        if order.status != 'PAID' or content.start_date <= seoul_today():
            raise HTTPException(409, '현재 상태에서는 전액 취소할 수 없습니다.')
        # Row lock and provider's currentCancellableAmount protect repeated/concurrent calls.
        self.provider.cancel_payment(order.payment_id, order.amount, reason)
        self.sync(order)
        if order.status != 'CANCELLED':
            raise HTTPException(409, '취소 처리 결과를 다시 확인해 주세요.')
        return order

    def webhook(self, body, headers):
        payload = self.provider.verify_webhook(body, headers)
        if not isinstance(payload, dict):
            raise HTTPException(400, '잘못된 웹훅 형식입니다.')
        if payload.get('type') not in ('Transaction.Paid', 'Transaction.Cancelled', 'Transaction.PartialCancelled'):
            return {'received': True}
        data = payload.get('data', {})
        if not isinstance(data, dict) or data.get('storeId') != self.settings.portone_store_id:
            raise HTTPException(400, '웹훅 상점 정보가 일치하지 않습니다.')
        payment_id = data.get('paymentId')
        if not isinstance(payment_id, str) or len(payment_id) > 64:
            raise HTTPException(400, '잘못된 결제 식별자입니다.')
        order = self.store.order(payment_id, lock=True)
        if not order:
            return {'received': True}
        event_id = headers.get('webhook-id', '')
        if not event_id or len(event_id) > 200:
            raise HTTPException(400, '잘못된 웹훅 식별자입니다.')
        if self.store.receipt(event_id):
            return {'received': True}
        self.sync(order)
        self.store.add(WebhookReceipt(event_id=event_id, payment_id=payment_id))
        return {'received': True}
