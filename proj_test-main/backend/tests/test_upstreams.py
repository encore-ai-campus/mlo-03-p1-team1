import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
from uuid import uuid4
import httpx
import pytest
from fastapi import Depends
from sqlalchemy import func, select
from standardwebhooks.webhooks import Webhook
from app.api.deps import get_payments, get_store
from app.collectors.culture_portal import CollectionError, CulturePortal
from app.core.config import Settings, get_settings
from app.core.security import seoul_today
from app.db.session import SessionLocal
from app.integrations.portone import PortOne
from app.main import app
from app.models import Content, PaymentHistory, Reservation
from app.pipelines.normalize import normalize
from app.services.payments import PaymentService

pytestmark = [pytest.mark.upstream, pytest.mark.skipif(os.environ.get('RUN_UPSTREAM_TESTS') != '1', reason='Start Postman simulation and set RUN_UPSTREAM_TESTS=1')]
BASE = os.environ.get('UPSTREAM_SIM_URL', 'http://127.0.0.1:4010/upstream')
WEBHOOK_SECRET = base64.b64encode(b'local-webhook-signature-test-only').decode()


@pytest.fixture
def settings():
    httpx.post(f'{BASE}/__test/reset').raise_for_status()
    settings = Settings(_env_file=None, database_url=get_settings().database_url, payments_enabled=True, refunds_enabled=True,
                        portone_api_secret='test-secret', portone_store_id='store-test', portone_channel_key='channel-test',
                        portone_webhook_secret=WEBHOOK_SECRET, portone_api_base_url=BASE,
                        culture_api_key='test-culture-key', culture_api_base_url=BASE)
    app.dependency_overrides[get_settings] = lambda: settings
    def payments(store=Depends(get_store)):
        return PaymentService(store, settings, PortOne(settings))
    app.dependency_overrides[get_payments] = payments
    return settings


@pytest.fixture
def order(client, auth, catalog, settings):
    response = client.post('/api/v1/payments/orders', headers={**auth, 'Idempotency-Key': str(uuid4())}, json={'content_id': catalog[0], 'quantity': 2})
    assert response.status_code == 201, response.text
    return response.json()


def provider_payment(order, **overrides):
    payment = {'id': order['payment_id'], 'status': 'PAID', 'storeId': 'store-test', 'amount': {'total': order['amount'], 'cancelled': 0},
               'currency': 'KRW', 'customData': json.dumps({'order_id': order['payment_id']})}
    payment.update(overrides)
    httpx.post(f'{BASE}/__test/payment', json=payment).raise_for_status()


def signed_payload(payment_id, event_id=None, timestamp=None, kind='Transaction.Paid'):
    data = json.dumps({'type': kind, 'data': {'paymentId': payment_id, 'storeId': 'store-test'}}, separators=(',', ':'))
    now = timestamp or datetime.now(timezone.utc); event_id = event_id or str(uuid4())
    return data, {'webhook-id': event_id, 'webhook-timestamp': str(int(now.timestamp())),
                  'webhook-signature': Webhook(WEBHOOK_SECRET).sign(event_id, now, data), 'Content-Type': 'application/json'}


def test_order_idempotency_and_server_amount(client, auth, catalog, settings):
    headers = {**auth, 'Idempotency-Key': str(uuid4())}; payload = {'content_id': catalog[0], 'quantity': 2}
    first = client.post('/api/v1/payments/orders', headers=headers, json=payload).json()
    second = client.post('/api/v1/payments/orders', headers=headers, json=payload).json()
    assert first['payment_id'] == second['payment_id'] and first['amount'] == 20000
    assert client.post('/api/v1/payments/orders', headers=headers, json={**payload, 'quantity': 3}).status_code == 409


def test_samples_cannot_be_purchased(client, auth, catalog, settings):
    with SessionLocal.begin() as db: db.get(Content, catalog[0]).is_sample = True
    assert client.post('/api/v1/payments/orders', headers={**auth, 'Idempotency-Key': str(uuid4())}, json={'content_id': catalog[0]}).status_code == 403


def test_verification_creates_exactly_one_reservation(client, auth, order):
    provider_payment(order); path = f'/api/v1/payments/{order["payment_id"]}/verify'
    for _ in range(2): assert client.post(path, headers=auth).json()['status'] == 'PAID'
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Reservation)) == 1
        assert db.scalar(select(func.count()).select_from(PaymentHistory)) == 1


@pytest.mark.parametrize('overrides', [{'amount': {'total': 1}}, {'currency': 'USD'}, {'storeId': 'wrong-store'}, {'customData': '{"order_id":"another-order"}'}])
def test_tampered_payment_does_not_confirm(client, auth, order, overrides):
    provider_payment(order, **overrides)
    assert client.post(f'/api/v1/payments/{order["payment_id"]}/verify', headers=auth).status_code == 409
    assert client.get('/api/v1/reservations', headers=auth).json() == []
    assert client.get('/api/v1/payments', headers=auth).json()[0]['status'] == 'PENDING'


def test_other_user_cannot_verify_order(client, order):
    other = client.post('/api/v1/auth/register', json={'email': 'other@example.com', 'name': '다른 회원', 'password': 'OtherPassword123!'}).json()
    assert client.post(f'/api/v1/payments/{order["payment_id"]}/verify', headers={'Authorization': f'Bearer {other["access_token"]}'}).status_code == 404


def test_upstream_failures_leave_order_pending(client, auth, order):
    provider_payment(order)
    for mode in ['failure', 'malformed']:
        httpx.post(f'{BASE}/__test/mode', json={'mode': mode}).raise_for_status()
        assert client.post(f'/api/v1/payments/{order["payment_id"]}/verify', headers=auth).status_code == 502
        assert client.get('/api/v1/payments', headers=auth).json()[0]['status'] == 'PENDING'
        assert client.get('/api/v1/reservations', headers=auth).json() == []


def test_signed_webhook_deduplicates_and_rejects_forgery(client, auth, order):
    provider_payment(order); data, headers = signed_payload(order['payment_id'])
    for _ in range(2): assert client.post('/api/v1/payments/webhook', headers=headers, content=data).status_code == 200
    assert len(client.get('/api/v1/reservations', headers=auth).json()) == 1
    for signature in ['v1,AAAA', 'garbage']:
        assert client.post('/api/v1/payments/webhook', headers={**headers, 'webhook-signature': signature}, content=data).status_code == 400
    old_data, old_headers = signed_payload(order['payment_id'], timestamp=datetime.now(timezone.utc) - timedelta(minutes=10))
    assert client.post('/api/v1/payments/webhook', headers=old_headers, content=old_data).status_code == 400


def test_unknown_webhook_is_ignored(client, settings):
    data, headers = signed_payload('unknown-id', kind='NewEvent.Future')
    assert client.post('/api/v1/payments/webhook', headers=headers, content=data).status_code == 200


def test_full_cancellation_is_idempotent(client, auth, order):
    provider_payment(order)
    assert client.post(f'/api/v1/payments/{order["payment_id"]}/verify', headers=auth).status_code == 200
    for _ in range(2):
        response = client.post(f'/api/v1/payments/{order["payment_id"]}/cancel', headers=auth, json={'reason': '개인 일정 변경'})
        assert response.status_code == 200, response.text
        assert response.json()['status'] == 'CANCELLED'
    assert httpx.get(f'{BASE}/__test/state').json()['cancellations'] == 1
    assert client.get('/api/v1/reservations', headers=auth).json()[0]['status'] == 'CANCELLED'


def test_refunds_require_policy_activation(client, auth, order, settings):
    settings.refunds_enabled = False; provider_payment(order)
    assert client.post(f'/api/v1/payments/{order["payment_id"]}/cancel', headers=auth, json={'reason': '개인 일정 변경'}).status_code == 403
    assert httpx.get(f'{BASE}/__test/state').json()['cancellations'] == 0


def test_partial_cancellation_requires_review(client, auth, order):
    provider_payment(order); client.post(f'/api/v1/payments/{order["payment_id"]}/verify', headers=auth)
    provider_payment(order, status='PARTIAL_CANCELLED', amount={'total': order['amount'], 'cancelled': 10000})
    assert client.post(f'/api/v1/payments/{order["payment_id"]}/verify', headers=auth).json()['status'] == 'PARTIAL_CANCELLED'
    assert client.get('/api/v1/reservations', headers=auth).json()[0]['status'] == 'REVIEW_REQUIRED'


def test_collector_http_normalization_and_error(settings):
    rows = list(CulturePortal(settings).collect(seoul_today(), seoul_today() + timedelta(days=90)))
    assert len(rows) == 1
    value = normalize(rows[0])
    assert value['source_id'] == 'mock-1' and value['price_text'] == '무료' and value['category'] == '전시'
    assert value['description'] == '공개 API 수집 테스트 전시입니다.'
    settings.culture_api_key = 'bad-key'
    with pytest.raises(CollectionError): list(CulturePortal(settings).collect(seoul_today(), seoul_today() + timedelta(days=90)))


def test_concurrent_order_key_creates_one_order(client, auth, catalog, settings):
    headers = {**auth, 'Idempotency-Key': str(uuid4())}
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(lambda _: client.post('/api/v1/payments/orders', headers=headers, json={'content_id': catalog[0]}), range(3)))
    assert [r.status_code for r in responses] == [201, 201, 201]
    assert len({r.json()['payment_id'] for r in responses}) == 1


def test_concurrent_verification_creates_one_reservation(client, auth, order):
    provider_payment(order)
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(lambda _: client.post(f'/api/v1/payments/{order["payment_id"]}/verify', headers=auth), range(3)))
    assert [r.status_code for r in responses] == [200, 200, 200]
    assert len(client.get('/api/v1/reservations', headers=auth).json()) == 1


def test_collector_upsert_and_failure_preserves_existing(settings, monkeypatch):
    from app.tasks import collect as task
    monkeypatch.setattr(task, 'get_settings', lambda: settings)
    assert task.collect(pages=1) == 1
    assert task.collect(pages=1) == 1
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Content)) == 1
    httpx.post(f'{BASE}/__test/mode', json={'mode': 'failure'}).raise_for_status()
    with pytest.raises(CollectionError): task.collect(pages=1)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Content)) == 1


def test_concurrent_cancellation_calls_provider_once(client, auth, order):
    provider_payment(order)
    client.post(f'/api/v1/payments/{order["payment_id"]}/verify', headers=auth)
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(lambda _: client.post(f'/api/v1/payments/{order["payment_id"]}/cancel', headers=auth, json={'reason': '동시 취소 테스트'}), range(3)))
    assert [r.status_code for r in responses] == [200, 200, 200]
    assert httpx.get(f'{BASE}/__test/state').json()['cancellations'] == 1
    with SessionLocal() as db:
        records = list(db.scalars(select(PaymentHistory).order_by(PaymentHistory.id)))
        assert len(records) == 2 and records[-1].cancelled_amount == order['amount']


def test_cancelled_order_does_not_regress(client, auth, order):
    provider_payment(order)
    client.post(f'/api/v1/payments/{order["payment_id"]}/verify', headers=auth)
    client.post(f'/api/v1/payments/{order["payment_id"]}/cancel', headers=auth, json={'reason': '일정 변경'})
    provider_payment(order)
    assert client.post(f'/api/v1/payments/{order["payment_id"]}/verify', headers=auth).json()['status'] == 'CANCELLED'
    assert client.get('/api/v1/reservations', headers=auth).json()[0]['status'] == 'CANCELLED'
