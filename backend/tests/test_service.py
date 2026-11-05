from datetime import timedelta
from uuid import uuid4
from sqlalchemy import func, select
from app.core.security import password_hash, password_matches, utcnow
from app.db.session import SessionLocal
from app.models import AuthSession, BehaviorEvent, User
from app.pipelines.normalize import normalize


def test_password_hashes_are_salted_and_verified():
    first = password_hash('A password with spaces!')
    assert first != password_hash('A password with spaces!')
    assert password_matches('A password with spaces!', first)
    assert not password_matches('incorrect', first)
    assert not password_matches('password', 'malformed')


def test_auth_session_revocation_and_login(client, auth):
    assert client.get('/api/v1/users/me', headers=auth).status_code == 200
    with SessionLocal() as db:
        assert 'LocalTestPassword123!' not in db.scalar(select(User)).password_hash
        assert db.scalar(select(AuthSession)).token_hash != auth['Authorization'][7:]
    assert client.post('/api/v1/auth/logout', headers=auth).status_code == 200
    assert client.get('/api/v1/users/me', headers=auth).status_code == 401
    assert client.post('/api/v1/auth/login', json={'email': 'tester@example.com', 'password': 'wrong'}).status_code == 401
    assert client.post('/api/v1/auth/login', json={'email': 'TESTER@example.com', 'password': 'LocalTestPassword123!'}).status_code == 200


def test_expired_session_is_denied(client, auth):
    with SessionLocal.begin() as db:
        db.scalar(select(AuthSession)).expires_at = utcnow() - timedelta(seconds=1)
    assert client.get('/api/v1/users/me', headers=auth).status_code == 401


def test_registration_duplicate_and_validation(client, auth):
    assert client.post('/api/v1/auth/register', json={'email': 'tester@example.com', 'name': '다른 이름', 'password': 'ValidPassword123'}).status_code == 409
    assert client.post('/api/v1/auth/register', json={'email': 'bad', 'name': ' ', 'password': '123'}).status_code == 422
    assert client.patch('/api/v1/users/me', json={'name': '  '}, headers=auth).status_code == 422
    assert client.patch('/api/v1/users/me', json={'name': '새 이름'}, headers=auth).json()['name'] == '새 이름'


def test_catalog_filters_and_pagination(client, catalog):
    page = client.get('/api/v1/contents?size=2').json()
    assert page['total'] == 3 and len(page['items']) == 2
    assert client.get('/api/v1/contents?category=음악').json()['items'][0]['id'] == catalog[1]
    assert client.get('/api/v1/contents?region=부산').json()['total'] == 1
    assert client.get('/api/v1/contents?free_only=true').json()['items'][0]['id'] == catalog[2]
    assert client.get('/api/v1/contents?q=재즈').json()['total'] == 1
    assert client.get('/api/v1/contents?q=%25').json()['total'] == 0
    assert client.get('/api/v1/contents?include_ended=true').json()['total'] == 4
    assert client.get('/api/v1/contents?page=0').status_code == 422
    assert client.get('/api/v1/contents?from_date=2026-12-31&to_date=2026-01-01').status_code == 422
    assert client.get('/api/v1/contents/999999').status_code == 404


def test_bookmark_idempotency_and_user_isolation(client, catalog, auth):
    path = f'/api/v1/bookmarks/{catalog[0]}'
    assert client.put(path).status_code == 401
    for _ in range(2): assert client.put(path, headers=auth).status_code == 200
    assert client.get('/api/v1/bookmarks', headers=auth).json()['total'] == 1
    assert client.get(f'/api/v1/contents/{catalog[0]}', headers=auth).json()['bookmarked']
    other = client.post('/api/v1/auth/register', json={'email': 'other@example.com', 'name': '다른 회원', 'password': 'OtherPassword123!'}).json()
    assert client.get('/api/v1/bookmarks', headers={'Authorization': f'Bearer {other["access_token"]}'}).json()['total'] == 0
    for _ in range(2): assert client.delete(path, headers=auth).status_code == 200
    assert client.get('/api/v1/bookmarks', headers=auth).json()['total'] == 0


def test_reviews_upsert_rating_and_delete(client, catalog, auth):
    path = f'/api/v1/contents/{catalog[0]}/reviews/me'
    assert client.put(path, headers=auth, json={'rating': 6, 'body': '충분한 길이의 리뷰'}).status_code == 422
    assert client.put(path, headers=auth, json={'rating': 5, 'body': '정말 흥미로운 전시였어요.'}).status_code == 200
    assert client.put(path, headers=auth, json={'rating': 4, 'body': '다시 보고 싶은 전시입니다.'}).status_code == 200
    detail = client.get(f'/api/v1/contents/{catalog[0]}').json()
    assert detail['rating'] == 4 and detail['review_count'] == 1
    assert len(client.get(f'/api/v1/contents/{catalog[0]}/reviews').json()) == 1
    assert client.delete(path, headers=auth).status_code == 200
    assert client.get(f'/api/v1/contents/{catalog[0]}').json()['rating'] is None


def test_event_deduplication_and_history(client, catalog, auth):
    event = {'event_id': str(uuid4()), 'event_type': 'content_view', 'content_id': catalog[1]}
    for _ in range(2): assert client.post('/api/v1/history/events', json=event, headers=auth).status_code == 202
    with SessionLocal() as db: assert db.scalar(select(func.count()).select_from(BehaviorEvent)) == 1
    assert client.get('/api/v1/history', headers=auth).json()['items'][0]['id'] == catalog[1]
    assert client.post('/api/v1/history/events', json={'event_id': str(uuid4()), 'event_type': 'content_view'}, headers=auth).status_code == 422


def test_survey_changes_recommendation(client, catalog, auth):
    assert client.put('/api/v1/surveys/me', headers=auth, json={'categories': [], 'tags': []}).status_code == 422
    assert client.put('/api/v1/surveys/me', headers=auth, json={'categories': ['음악'], 'tags': ['재즈']}).status_code == 200
    result = client.get('/api/v1/recommendations', headers=auth).json()['items']
    assert result[0]['id'] == catalog[1] and '재즈' in result[0]['recommendation_reason']
    assert catalog[3] not in [item['id'] for item in result]
    client.put('/api/v1/surveys/me', headers=auth, json={'categories': ['전시'], 'tags': []})
    assert client.get('/api/v1/recommendations', headers=auth).json()['items'][0]['id'] == catalog[0]


def test_views_work_without_survey(client, catalog, auth):
    assert client.get('/api/v1/recommendations', headers=auth).json()['items'][0]['id'] == catalog[0]
    client.post('/api/v1/history/events', headers=auth, json={'event_id': str(uuid4()), 'event_type': 'content_view', 'content_id': catalog[1]})
    assert client.get('/api/v1/recommendations', headers=auth).json()['items'][0]['id'] == catalog[1]


def test_legacy_pg_payment_disabled_does_not_create_order(client, catalog, auth):
    config = client.get('/api/v1/payments/config').json()
    assert config['enabled'] and config['mode'] == 'simulation'
    assert not config['refunds_enabled']
    assert client.post('/api/v1/payments/orders', headers={**auth, 'Idempotency-Key': str(uuid4())}, json={'content_id': catalog[0]}).status_code == 503
    assert client.get('/api/v1/payments', headers=auth).json() == []


def test_normalizer_tiered_price_and_html():
    value = normalize(dict(seq='123', title='&lt;b&gt;전시&lt;/b&gt;', startDate='20261101', endDate='20261201', realmName='미술', price='성인 2만원, 청소년 1만원', url='javascript:alert(1)', contents1='<p>전시 설명</p>', area='서울특별시'))
    assert value['title'] == '전시' and value['price'] == 0 and value['price_text'] != '무료'
    assert not value['bookable'] and not value['source_url'] and value['region'] == '서울'
    assert '<p>' not in value['description']


def test_cors_allows_configured_frontend_only(client):
    headers = {'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'authorization,content-type'}
    assert client.options('/api/v1/auth/login', headers=headers).status_code == 200
    headers['Origin'] = 'https://untrusted.example'
    assert client.options('/api/v1/auth/login', headers=headers).status_code == 400


def test_auth_rate_limit(client):
    for _ in range(20): assert client.post('/api/v1/auth/login', json={'email': 'missing@example.com', 'password': 'incorrect'}).status_code == 401
    assert client.post('/api/v1/auth/login', json={'email': 'missing@example.com', 'password': 'incorrect'}).status_code == 429
