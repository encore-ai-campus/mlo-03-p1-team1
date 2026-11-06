"""Run integration cases with a SELECT-only TEST_DATABASE_READ_URL on the replica."""
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.db import session as sessions
from app.repositories.store import Store


requires_replica = pytest.mark.skipif(sessions.read_engine is None, reason='Requires explicit TEST_DATABASE_READ_URL')


@contextmanager
def captured_statements(engine):
    statements = []
    def capture(connection, cursor, statement, parameters, context, many):
        statements.append(statement)
    event.listen(engine, 'before_cursor_execute', capture)
    try:
        yield statements
    finally:
        event.remove(engine, 'before_cursor_execute', capture)


@requires_replica
def test_replica_identity_and_account_cannot_write():
    with sessions.read_engine.connect() as conn:
        assert conn.scalar(text('SELECT @@server_id')) == 2
        assert conn.scalar(text('SELECT @@read_only')) == 1
        grants = [row[0].split(' IDENTIFIED BY')[0] for row in conn.execute(text('SHOW GRANTS'))]
        assert any('GRANT SELECT ON' in grant for grant in grants)
        assert not any(privilege in grant for grant in grants for privilege in
                       ('ALL PRIVILEGES', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'SUPER', 'READ ONLY ADMIN'))
        for statement in (
            'UPDATE contents SET title=title WHERE 1=0',
            'DELETE FROM contents WHERE 1=0',
            'INSERT INTO contents (id) SELECT 0 WHERE 1=0',
        ):
            with pytest.raises(OperationalError) as error:
                conn.execute(text(statement))
            # MariaDB may reject at read_only before checking the account's SELECT-only grant.
            assert error.value.orig.args[0] in (1142, 1290)
            conn.rollback()


@requires_replica
def test_catalog_endpoints_query_the_actual_replica(client, catalog):
    with captured_statements(sessions.read_engine) as sql:
        for path in ('/contents?size=2', f'/contents/{catalog[0]}', '/recommendations?size=2'):
            response = client.get('/api/v1' + path)
            assert response.status_code == 200, response.text
    assert sum('MASTER_GTID_WAIT' in statement for statement in sql) == 3
    assert sum('FROM contents' in statement for statement in sql) >= 3


@requires_replica
def test_writes_and_personal_state_stay_on_master(client, catalog, auth):
    with captured_statements(sessions.read_engine) as replica_sql:
        assert client.put(f'/api/v1/bookmarks/{catalog[0]}', headers=auth).status_code == 200
        assert client.patch('/api/v1/users/me', headers=auth, json={'name': '읽기분리검증'}).status_code == 200
        assert client.get('/api/v1/users/me', headers=auth).json()['name'] == '읽기분리검증'
        assert client.get('/api/v1/bookmarks', headers=auth).json()['items'][0]['id'] == catalog[0]
        assert client.get('/api/v1/payments', headers=auth).status_code == 200
    assert replica_sql == []
    # Catalog data comes from the replica; the just-written bookmark is enriched on master.
    with captured_statements(sessions.read_engine) as replica_sql:
        response = client.get(f'/api/v1/contents/{catalog[0]}', headers=auth)
        assert response.status_code == 200 and response.json()['bookmarked'] is True
    assert any('FROM contents' in sql for sql in replica_sql)
    assert not any('FROM auth_sessions' in sql or 'FROM bookmarks' in sql for sql in replica_sql)


def test_replica_connection_failure_falls_back_to_master(catalog, monkeypatch):
    unavailable = create_engine('mysql+pymysql://unused:unused@127.0.0.1:13399/unavailable_test',
                                connect_args={'connect_timeout': 1}, hide_parameters=True)
    monkeypatch.setattr(sessions, 'ReadSessionLocal', sessionmaker(bind=unavailable))
    try:
        with sessions.SessionLocal() as primary:
            with sessions.catalog_session(primary) as selected:
                assert selected is primary
                assert Store(primary, catalog_db=selected).content(catalog[0]).id == catalog[0]
    finally:
        unavailable.dispose()


@requires_replica
def test_gtid_timeout_uses_master_without_serving_stale_reads(monkeypatch):
    monkeypatch.setattr(sessions.settings, 'database_replica_wait_seconds', 0.05)
    primary = SimpleNamespace(scalar=lambda statement: '0-1-999999999999999')
    with sessions.catalog_session(primary) as selected:
        assert selected is primary


@requires_replica
def test_replica_query_failure_retries_catalog_read_on_master(client, catalog):
    injected = []
    def fail_catalog_query(connection, cursor, statement, parameters, context, many):
        if 'FROM contents' in statement and not injected:
            injected.append(True)
            raise OperationalError('test select', {}, RuntimeError('injected replica disconnect'))
    event.listen(sessions.read_engine, 'before_cursor_execute', fail_catalog_query)
    try:
        response = client.get('/api/v1/contents?size=2')
        assert response.status_code == 200 and len(response.json()['items']) == 2
        assert injected == [True]
    finally:
        event.remove(sessions.read_engine, 'before_cursor_execute', fail_catalog_query)
