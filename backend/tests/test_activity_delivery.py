from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import os

import pytest
from pymongo.errors import AutoReconnect
from sqlalchemy import func, select

from app.core.security import utcnow
from app.db.session import SessionLocal
from app.models import BehaviorEvent, EventOutbox
from app.repositories.events import event_document
from app.repositories.store import Store
from app.services import events as delivery


def guest_event(**overrides):
    return {'event_id': str(uuid4()), 'event_type': 'page_view', 'page_path': '/explore',
            'anonymous_id': str(uuid4()), 'session_id': str(uuid4()), **overrides}


def test_guest_events_and_sensitive_or_forged_fields(client):
    event = guest_event()
    assert client.post('/api/v1/history/events', json=event).status_code == 202
    with SessionLocal() as db:
        row = db.get(BehaviorEvent, event['event_id'])
        document = event_document(row)
        assert document['user_id'] is None
        assert document['session_id'] == event['session_id']
        assert document['occurred_at'].tzinfo is not None
        assert db.get(EventOutbox, event['event_id']).delivered_at is None
    for extra in ({'user_id': 1}, {'occurred_at': '2020-01-01'}, {'password': 'secret'},
                  {'page_path': '/payment/result?token=secret'}, {'page_path': 'https://outside.test'}):
        assert client.post('/api/v1/history/events', json=guest_event(**extra)).status_code == 422
    assert client.post('/api/v1/history/events', json=guest_event(event_type='payment_completed')).status_code == 422
    assert client.post('/api/v1/history/events', json={'event_id': str(uuid4()), 'event_type': 'search'}).status_code == 422


def test_duplicate_event_is_immutable_and_has_one_outbox_record(client, auth):
    event = guest_event()
    assert client.post('/api/v1/history/events', json=event, headers=auth).status_code == 202
    assert client.post('/api/v1/history/events', json={**event, 'page_path': '/mypage'}).status_code == 202
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(EventOutbox)) == 1
        saved = db.get(BehaviorEvent, event['event_id'])
        assert saved.user_id is not None
        assert saved.properties['_context']['page_path'] == '/explore'


def test_outbox_not_visible_before_commit_and_removed_on_rollback():
    event_id = str(uuid4())
    with SessionLocal() as producer:
        Store(producer).event({'event_id': event_id, 'event_type': 'search'})
        with SessionLocal() as observer:
            assert observer.get(EventOutbox, event_id) is None
        producer.rollback()
    with SessionLocal() as observer:
        assert observer.get(BehaviorEvent, event_id) is None
        assert observer.get(EventOutbox, event_id) is None


def test_mongo_failure_is_durable_and_retried_after_recovery(client, auth, monkeypatch):
    event = guest_event()
    assert client.post('/api/v1/history/events', json=event, headers=auth).status_code == 202
    def unavailable(row):
        raise AutoReconnect('Deliberately unavailable; no real URI')
    monkeypatch.setattr(delivery, 'deliver', unavailable)
    assert delivery.dispatch_batch() == 0
    with SessionLocal.begin() as db:
        pending = db.get(EventOutbox, event['event_id'])
        assert pending.attempts == 1 and pending.delivered_at is None
        assert pending.last_error == 'AutoReconnect'
        pending.next_attempt_at = utcnow() - timedelta(seconds=1)
    received = []
    monkeypatch.setattr(delivery, 'deliver', lambda row: received.append(event_document(row)))
    assert delivery.dispatch_batch() == 1
    assert delivery.dispatch_batch() == 0
    assert received[0]['event_id'] == event['event_id']
    with SessionLocal() as db:
        pending = db.get(EventOutbox, event['event_id'])
        assert pending.attempts == 2 and pending.delivered_at is not None and pending.last_error is None


def test_bookmark_failure_never_emits_committed_success_event(client, auth):
    assert client.put('/api/v1/bookmarks/2147483647', headers=auth).status_code == 404
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(EventOutbox)) == 0


def test_context_headers_link_authoritative_bookmarks_to_browser(client, catalog, auth):
    sid, aid = str(uuid4()), str(uuid4())
    headers = {**auth, 'X-Activity-Session-Id': sid, 'X-Activity-Anonymous-Id': aid, 'X-Activity-Page': f'/contents/{catalog[0]}'}
    assert client.put(f'/api/v1/bookmarks/{catalog[0]}', headers=headers).status_code == 200
    with SessionLocal() as db:
        document = event_document(db.scalar(select(BehaviorEvent)))
        assert document['source'] == 'server'
        assert document['session_id'] == sid and document['anonymous_id'] == aid
        assert document['content_id'] == catalog[0]


def test_two_delivery_workers_claim_each_committed_event_once(client, auth, monkeypatch):
    event_ids = {str(uuid4()) for _ in range(8)}
    for event_id in event_ids:
        assert client.post('/api/v1/history/events', json=guest_event(event_id=event_id), headers=auth).status_code == 202
    received = []
    monkeypatch.setattr(delivery, 'deliver', lambda row: received.append(row.event_id))
    with ThreadPoolExecutor(max_workers=2) as pool:
        counts = list(pool.map(lambda _: delivery.dispatch_batch(), range(2)))
    assert sum(counts) == 8
    assert len(received) == len(set(received)) == 8 and set(received) == event_ids


@pytest.mark.skipif(os.environ.get('RUN_MONGO_TESTS') != '1', reason='Explicit opt-in for real MongoDB integration')
def test_real_mongo_validator_and_idempotent_delivery(client, auth, monkeypatch):
    from app.core.config import get_settings
    from app.db.mongo import user_events
    from app.repositories.events import deliver
    from app.tasks.setup_events_mongo import setup
    from pymongo.errors import WriteError
    settings = get_settings()
    monkeypatch.setattr(settings, 'mongodb_database', 'oddinary_activity_test')
    setup()
    event = guest_event()
    assert client.post('/api/v1/history/events', json=event, headers=auth).status_code == 202
    col = user_events()
    try:
        with SessionLocal() as db:
            row = db.get(BehaviorEvent, event['event_id'])
            deliver(row)
            deliver(row)  # Mongo acknowledged but SQL ack lost: the replay is safe.
        assert col.count_documents({'event_id': event['event_id']}) == 1
        document = col.find_one({'_id': event['event_id']})
        assert document['schema_version'] == 1 and document['user_id'] is not None
        invalid_id = str(uuid4())
        invalid = {**document, '_id': invalid_id, 'event_id': invalid_id, 'password': 'must-be-rejected'}
        with pytest.raises(WriteError) as error:
            col.insert_one(invalid)
        assert error.value.code == 121  # Document validation, not a coincidental duplicate-key failure.
    finally:
        col.delete_one({'_id': event['event_id']})
