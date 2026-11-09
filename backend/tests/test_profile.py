import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import User


PROFILE = {'name': '문화생활', 'gender': 'female', 'age': 28, 'residence': '서울',
           'occupation': '개발자', 'mbti': 'INFP'}


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
