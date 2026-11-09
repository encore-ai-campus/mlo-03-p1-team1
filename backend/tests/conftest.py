import os
from pathlib import Path
from datetime import timedelta
from dotenv import dotenv_values
import pytest
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
test_url = os.environ.get('TEST_DATABASE_URL') or dotenv_values(ROOT / '.runtime/test.env').get('TEST_DATABASE_URL')
if not test_url or not make_url(test_url).database.endswith('_test'):
    raise RuntimeError('Set TEST_DATABASE_URL to a dedicated MariaDB database ending in _test. Tests never use the development database or SQLite.')
os.environ['DATABASE_URL'] = test_url

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from app.api.deps import _attempts
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models import Content
from app.core.security import seoul_today


@pytest.fixture(scope='session', autouse=True)
def migrated_database():
    command.upgrade(Config(str(ROOT / 'backend/alembic.ini')), 'head')
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_database(migrated_database):
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    _attempts.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def catalog():
    rows = []
    with SessionLocal.begin() as db:
        for i, category in enumerate(['전시', '음악', '연극', '전시']):
            content = Content(source='test', source_id=str(i), title=['테스트 전시', '테스트 재즈', '무료 연극', '종료 전시'][i], subtitle='', category=category,
                              region='서울' if i != 1 else '부산', venue='테스트 공간', address='',
                              start_date=seoul_today() + timedelta(days=10), end_date=seoul_today() + timedelta(days=30),
                              price=0 if i == 2 else 10000, price_text='무료' if i == 2 else '10,000원', description='테스트 콘텐츠 소개',
                              image_url='', source_url='', tags=['재즈'] if i == 1 else ['현대미술'], is_sample=False, bookable=i == 0)
            if i == 3:
                content.start_date = seoul_today() - timedelta(days=30)
                content.end_date = seoul_today() - timedelta(days=1)
            db.add(content); db.flush(); rows.append(content.id)
    return rows


@pytest.fixture
def auth(client):
    response = client.post('/api/v1/auth/register', json={'email': 'tester@example.com', 'name': '테스터', 'password': 'LocalTestPassword123!'})
    assert response.status_code == 201, response.text
    return {'Authorization': f'Bearer {response.json()["access_token"]}'}
