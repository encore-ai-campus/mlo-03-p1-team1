import pytest
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import AuthSession, User


PROFILE = {'name': '문화생활', 'gender': 'female', 'age': 28, 'residence': '서울',
           'occupation': '개발자', 'mbti': 'INFP'}


def test_registration_saves_profile_and_survey_together(client):
    payload = {**PROFILE, 'email': 'onboarding@example.com', 'password': 'OnboardingPassword123!',
               'occupation': '  개발자  ', 'mbti': ' infp ',
               'survey': {'categories': ['전시', '음악', '전시'], 'tags': ['재즈', ' 재즈 ', '사진']}}
    response = client.post('/api/v1/auth/register', json=payload)
    assert response.status_code == 201, response.text
    result = response.json()
    saved = result['user']
    assert saved['survey_completed'] is True
    assert saved['categories'] == ['전시', '음악']
    assert saved['tags'] == ['재즈', '사진']
    for field, value in PROFILE.items():
        assert saved[field] == value
    assert saved['age_recorded_at'].endswith('Z')
    headers = {'Authorization': f'Bearer {result["access_token"]}'}
    assert client.get('/api/v1/users/me', headers=headers).json() == saved
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 200
    login = client.post('/api/v1/auth/login', json={
        'email': payload['email'], 'password': payload['password'],
    })
    assert login.status_code == 200
    assert login.json()['user'] == saved


def test_registration_optional_profile_can_be_empty(client):
    response = client.post('/api/v1/auth/register', json={
        'email': 'optional@example.com', 'password': 'OptionalPassword123!', 'name': '선택정보',
        'gender': None, 'age': None, 'residence': None, 'occupation': '', 'mbti': '',
        'survey': {'categories': ['전시'], 'tags': []},
    })
    assert response.status_code == 201, response.text
    saved = response.json()['user']
    assert saved['survey_completed']
    for field in ('gender', 'age', 'age_recorded_at', 'residence', 'occupation', 'mbti'):
        assert saved[field] is None


@pytest.mark.parametrize('extra', [
    {'age': -1}, {'age': 121}, {'age': '28'}, {'age': True}, {'age': 20.5},
    {'gender': 'unknown'}, {'residence': '없는 지역'}, {'mbti': 'ABCD'},
    {'occupation': 'a' * 81}, {'age_recorded_at': '2026-01-01T00:00:00Z'},
    {'survey': {'categories': [], 'tags': []}},
    {'survey': {'categories': ['없는 분야'], 'tags': []}},
    {'survey': {'categories': ['전시'], 'tags': ['태그'] * 11}},
])
def test_invalid_registration_profile_or_survey_creates_no_account(client, extra):
    response = client.post('/api/v1/auth/register', json={
        'email': 'invalid-onboarding@example.com', 'name': '입력검증',
        'password': 'ValidationPassword123!', **extra,
    })
    assert response.status_code == 422, response.text
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
        assert db.scalar(select(func.count()).select_from(AuthSession)) == 0


def test_registration_rolls_back_profile_and_survey_when_session_fails(client, monkeypatch):
    def fail_session(*args):
        raise RuntimeError('session creation failed')
    payload = {**PROFILE, 'email': 'rollback@example.com', 'password': 'RollbackPassword123!',
               'survey': {'categories': ['전시'], 'tags': ['사진']}}
    with monkeypatch.context() as patch:
        patch.setattr('app.services.auth.create_session', fail_session)
        with pytest.raises(RuntimeError, match='session creation failed'):
            client.post('/api/v1/auth/register', json=payload)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
        assert db.scalar(select(func.count()).select_from(AuthSession)) == 0
    # The same email can be submitted again after the failed transaction.
    assert client.post('/api/v1/auth/register', json=payload).status_code == 201


def test_profile_requires_authentication(client):
    assert client.get('/api/v1/users/me').status_code == 401
    assert client.patch('/api/v1/users/me', json=PROFILE).status_code == 401


def test_profile_defaults_and_persistence_across_login(client, auth):
    original = client.get('/api/v1/users/me', headers=auth).json()
    for field in ('gender', 'age', 'age_recorded_at', 'residence', 'occupation', 'mbti'):
        assert original[field] is None
    response = client.patch('/api/v1/users/me', headers=auth, json={
        **PROFILE, 'name': '  문화생활  ', 'occupation': '  개발자  ', 'mbti': ' infp ',
    })
    assert response.status_code == 200, response.text
    saved = response.json()
    for field, value in PROFILE.items():
        assert saved[field] == value
    assert saved['age_recorded_at'].endswith('Z')
    assert saved['email'] == original['email']
    assert 'password_hash' not in saved
    with SessionLocal() as db:
        user = db.get(User, original['id'])
        assert (user.age, user.residence, user.occupation, user.mbti) == (28, '서울', '개발자', 'INFP')
        assert user.age_recorded_at is not None
    assert client.post('/api/v1/auth/logout', headers=auth).status_code == 200
    login = client.post('/api/v1/auth/login', json={'email': original['email'], 'password': 'LocalTestPassword123!'}).json()
    assert login['user'] == saved
    assert not login['user']['survey_completed']


def test_profile_patch_preserves_omitted_fields_and_can_clear_values(client, auth):
    saved = client.patch('/api/v1/users/me', headers=auth, json=PROFILE).json()
    updated = client.patch('/api/v1/users/me', headers=auth, json={'occupation': '프리랜서'}).json()
    assert updated['name'] == PROFILE['name']
    assert updated['age'] == PROFILE['age']
    assert updated['age_recorded_at'] == saved['age_recorded_at']
    cleared = client.patch('/api/v1/users/me', headers=auth, json={
        'gender': None, 'age': None, 'residence': None, 'occupation': '   ', 'mbti': '',
    })
    assert cleared.status_code == 200, cleared.text
    for field in ('gender', 'age', 'age_recorded_at', 'residence', 'occupation', 'mbti'):
        assert cleared.json()[field] is None
    assert cleared.json()['name'] == PROFILE['name']
    assert client.get('/api/v1/users/me', headers=auth).json() == cleared.json()


@pytest.mark.parametrize('data', [
    {'name': None}, {'name': '  '}, {'name': 'a' * 41},
    {'age': -1}, {'age': 121}, {'age': 20.5}, {'age': '28'}, {'age': True},
    {'gender': 'unknown'}, {'residence': '없는 지역'}, {'occupation': 'a' * 81},
    {'mbti': 'ABCD'}, {'mbti': 'INFPP'},
    {'email': 'changed@example.com'}, {'id': 999}, {'survey_completed': True},
    {'categories': ['음악']}, {'password_hash': 'unsafe'}, {'age_recorded_at': '2020-01-01T00:00:00Z'},
])
def test_invalid_profile_update_is_atomic(client, auth, data):
    before = client.get('/api/v1/users/me', headers=auth).json()
    response = client.patch('/api/v1/users/me', headers=auth, json={'occupation': '바뀌면 안 됨', **data})
    assert response.status_code == 422, response.text
    assert client.get('/api/v1/users/me', headers=auth).json() == before


@pytest.mark.parametrize('age', [0, 120])
def test_age_boundaries(client, auth, age):
    response = client.patch('/api/v1/users/me', headers=auth, json={'age': age})
    assert response.status_code == 200, response.text
    assert response.json()['age'] == age


def test_profile_updates_are_isolated_and_survey_preserves_demographics(client, auth):
    client.patch('/api/v1/users/me', headers=auth, json=PROFILE).raise_for_status()
    other = client.post('/api/v1/auth/register', json={
        'email': 'other@example.com', 'name': '다른회원', 'password': 'OtherPassword123!',
    }).json()
    other_auth = {'Authorization': f'Bearer {other["access_token"]}'}
    assert other['user']['age'] is None
    client.patch('/api/v1/users/me', headers=other_auth, json={'mbti': 'ESTJ'}).raise_for_status()
    response = client.put('/api/v1/surveys/me', headers=auth, json={'categories': ['음악'], 'tags': ['재즈']})
    assert response.status_code == 200, response.text
    assert response.json()['survey_completed']
    for field, value in PROFILE.items():
        assert response.json()[field] == value
    assert client.get('/api/v1/users/me', headers=other_auth).json()['mbti'] == 'ESTJ'
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.id == other['user']['id'])).age is None
