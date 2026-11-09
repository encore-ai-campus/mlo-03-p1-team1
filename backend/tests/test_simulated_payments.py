from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.security import seoul_today
from app.db.session import SessionLocal
from app.integrations.portone import PortOne
from app.models import BehaviorEvent, Content, Order, PaymentHistory, Reservation
from app.repositories.store import Store


def pay(client, auth, content_id, quantity=1, key=None, **extra):
    return client.post('/api/v1/payments/simulations',
                       headers={**auth, 'Idempotency-Key': key or str(uuid4())},
                       json={'content_id': content_id, 'quantity': quantity, **extra})


def counts():
    with SessionLocal() as db:
        return [db.scalar(select(func.count()).select_from(model))
                for model in (Order, PaymentHistory, Reservation, BehaviorEvent)]


def test_payment_and_history_require_login(client, catalog):
    assert pay(client, {}, catalog[0]).status_code == 401
    for path in ('/payments', '/reservations', '/payments/sim-unknown'):
        assert client.get('/api/v1' + path).status_code == 401
    assert counts() == [0, 0, 0, 0]


def test_sample_payment_records_server_amount_usage_and_event_without_pg(client, auth, catalog, monkeypatch):
    def reject_pg(*args, **kwargs):
        pytest.fail('A simulated payment must never initialize the PG adapter')
    monkeypatch.setattr(PortOne, '__init__', reject_pg)
    with SessionLocal.begin() as db:
        content = db.get(Content, catalog[0])
        content.is_sample = True
        content.bookable = False
        content.start_date = seoul_today() - timedelta(days=1)

    response = pay(client, auth, catalog[0], quantity=2)
    assert response.status_code == 201, response.text
    order = response.json()
    assert order['payment_id'].startswith('sim-')
    assert order['status'] == 'PAID' and order['is_simulated'] is True
    assert order['amount'] == 20000 and order['quantity'] == 2 and order['currency'] == 'KRW'
    assert client.get('/api/v1/payments', headers=auth).json() == [order]
    assert client.get('/api/v1/payments/' + order['payment_id'], headers=auth).json() == order
    usage = client.get('/api/v1/reservations', headers=auth).json()
    assert len(usage) == 1 and usage[0]['payment_id'] == order['payment_id']
    assert usage[0]['is_simulated'] and usage[0]['status'] == 'CONFIRMED' and usage[0]['amount'] == 20000
    assert counts() == [1, 1, 1, 1]
    with SessionLocal() as db:
        event = db.scalar(select(BehaviorEvent))
        saved = db.scalar(select(Order))
        assert event.user_id == saved.user_id and event.content_id == catalog[0]
        assert event.event_type == 'payment_completed'
        assert event.properties == {'payment_id': order['payment_id'], 'payment_mode': 'simulation',
                                    'quantity': 2, 'amount': 20000, 'currency': 'KRW'}


def test_same_key_is_idempotent_even_after_price_changes(client, auth, catalog):
    key = str(uuid4())
    first = pay(client, auth, catalog[0], key=key).json()
    with SessionLocal.begin() as db:
        db.get(Content, catalog[0]).price = 20000
    second = pay(client, auth, catalog[0], key=key)
    assert second.status_code == 201 and second.json() == first
    assert pay(client, auth, catalog[0], quantity=2, key=key).status_code == 409
    assert pay(client, auth, catalog[1], key=key).status_code == 409
    assert counts() == [1, 1, 1, 1]


def test_concurrent_retries_create_one_payment_usage_and_event(client, auth, catalog):
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(lambda _: pay(client, auth, catalog[0], key=key), range(3)))
    assert [response.status_code for response in responses] == [201, 201, 201]
    assert len({response.json()['payment_id'] for response in responses}) == 1
    assert counts() == [1, 1, 1, 1]


def test_history_is_private_and_persists_after_login(client, auth, catalog):
    order = pay(client, auth, catalog[0]).json()
    other = client.post('/api/v1/auth/register', json={
        'email': 'other@example.com', 'name': '다른 사용자', 'password': 'OtherPassword123!',
    }).json()
    other_auth = {'Authorization': 'Bearer ' + other['access_token']}
    assert client.get('/api/v1/payments', headers=other_auth).json() == []
    assert client.get('/api/v1/reservations', headers=other_auth).json() == []
    assert client.get('/api/v1/payments/' + order['payment_id'], headers=other_auth).status_code == 404
    assert client.post('/api/v1/auth/logout', headers=auth).status_code == 200
    assert pay(client, auth, catalog[0]).status_code == 401
    login = client.post('/api/v1/auth/login', json={'email': 'tester@example.com', 'password': 'LocalTestPassword123!'}).json()
    headers = {'Authorization': 'Bearer ' + login['access_token']}
    assert client.get('/api/v1/payments', headers=headers).json() == [order]


@pytest.mark.parametrize('quantity', [0, 5, -1, 1.5, True, '2'])
def test_invalid_quantity_cannot_record_a_payment(client, auth, catalog, quantity):
    assert pay(client, auth, catalog[0], quantity=quantity).status_code == 422
    assert counts() == [0, 0, 0, 0]


@pytest.mark.parametrize('extra', [{'amount': 1}, {'user_id': 999}, {'status': 'PAID'}])
def test_client_cannot_set_price_owner_or_status(client, auth, catalog, extra):
    assert pay(client, auth, catalog[0], **extra).status_code == 422
    assert counts() == [0, 0, 0, 0]


def test_free_ended_missing_and_invalid_keys_are_rejected(client, auth, catalog):
    assert pay(client, auth, catalog[2]).status_code == 403
    assert pay(client, auth, catalog[3]).status_code == 409
    assert pay(client, auth, 999999999).status_code == 404
    assert pay(client, auth, catalog[0], key='invalid').status_code == 422
    assert client.post('/api/v1/payments/simulations', headers=auth, json={'content_id': catalog[0]}).status_code == 422
    assert counts() == [0, 0, 0, 0]


@pytest.mark.parametrize('failure', ['history', 'usage', 'event'])
def test_partial_storage_failure_rolls_back_every_record(client, auth, catalog, monkeypatch, failure):
    original_add = Store.add
    def add(store, value):
        if (failure == 'history' and isinstance(value, PaymentHistory)) or (failure == 'usage' and isinstance(value, Reservation)):
            raise RuntimeError('injected database write failure')
        return original_add(store, value)
    def event(store, values):
        raise RuntimeError('injected event write failure')
    monkeypatch.setattr(Store, 'add', add)
    if failure == 'event':
        monkeypatch.setattr(Store, 'event', event)
    with pytest.raises(RuntimeError):
        pay(client, auth, catalog[0])
    assert counts() == [0, 0, 0, 0]
