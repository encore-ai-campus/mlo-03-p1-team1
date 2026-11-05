from app.core.config import get_settings


def test_preferences_validation_and_roundtrip(client, auth):
    payload = {'categories': ['전시'], 'tags': ['사진'], 'preferences': {
        'regions': ['부산'], 'max_price': 20000, 'companions': ['혼자', '가족']}}
    response = client.put('/api/v1/surveys/me', json=payload, headers=auth)
    assert response.status_code == 200, response.text
    assert client.get('/api/v1/users/me', headers=auth).json()['preferences'] == payload['preferences']
    payload['preferences']['max_price'] = -1
    assert client.put('/api/v1/surveys/me', json=payload, headers=auth).status_code == 422


def test_own_reviews_are_isolated(client, auth, catalog):
    client.put(f'/api/v1/contents/{catalog[0]}/reviews/me', headers=auth, json={'rating': 4, 'body': '내가 작성한 관람 후기입니다.'})
    own = client.get('/api/v1/users/me/reviews', headers=auth).json()
    assert len(own) == 1 and own[0]['content_id'] == catalog[0]
    assert own[0]['content_title'] == '테스트 전시'
    assert client.get('/api/v1/users/me/reviews').status_code == 401


def test_attendance_is_idempotent_and_private(client, auth, catalog):
    path = f'/api/v1/visits/{catalog[0]}'
    assert client.put(path).status_code == 401
    for _ in range(2):
        assert client.put(path, headers=auth).status_code == 200
    assert client.get('/api/v1/visits', headers=auth).json()['total'] == 1
    client.delete(path, headers=auth)
    assert client.get('/api/v1/visits', headers=auth).json()['total'] == 0


def test_similar_excludes_self_and_ended(client, catalog):
    result = client.get(f'/api/v1/contents/{catalog[0]}/similar').json()
    assert {c['id'] for c in result['items']} == set(catalog[1:3])


def test_price_bounds_and_genre_search(client, catalog):
    assert client.get('/api/v1/contents?max_price=0').json()['total'] == 1
    assert client.get('/api/v1/contents?min_price=1&max_price=10000').json()['total'] == 2
    assert client.get('/api/v1/contents?min_price=20000&max_price=10').status_code == 422
    assert client.get('/api/v1/contents?q=음악').json()['total'] == 1


def test_admin_is_server_authorized_and_aggregates_only(client, auth, catalog, monkeypatch):
    assert client.get('/api/v1/admin/overview').status_code == 401
    assert client.get('/api/v1/admin/overview', headers=auth).status_code == 403
    monkeypatch.setattr(get_settings(), 'admin_emails', ['tester@example.com'])
    response = client.get('/api/v1/admin/overview', headers=auth)
    assert response.status_code == 200
    assert response.json()['counts']['contents'] == 4
    assert 'tester@example.com' not in response.text
    assert client.get('/api/v1/users/me', headers=auth).json()['is_admin'] is True


def test_collection_audit_records_success(monkeypatch):
    from sqlalchemy import select
    from app.tasks import collect as task
    from app.db.session import SessionLocal
    from app.models import CollectionRun
    monkeypatch.setattr(task, '_collect', lambda days, pages: 3)
    assert task.collect() == 3
    with SessionLocal() as db:
        run = db.scalar(select(CollectionRun))
        assert run.status == 'SUCCESS' and run.collected_count == 3 and run.finished_at


def test_collection_audit_redacts_failure_details(monkeypatch):
    import pytest
    from sqlalchemy import select
    from app.tasks import collect as task
    from app.db.session import SessionLocal
    from app.models import CollectionRun
    def fail(days, pages):
        raise ValueError('secret-provider-key-must-not-be-recorded')
    monkeypatch.setattr(task, '_collect', fail)
    with pytest.raises(ValueError):
        task.collect()
    with SessionLocal() as db:
        run = db.scalar(select(CollectionRun))
        assert run.status == 'FAILED' and run.error_code == 'ValueError'
        assert 'secret' not in run.error_code
