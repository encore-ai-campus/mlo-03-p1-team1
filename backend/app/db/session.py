from contextlib import contextmanager
import logging
import math

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True, pool_recycle=1800,
                       connect_args={'connect_timeout': 5}, hide_parameters=True, isolation_level='READ COMMITTED')
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

settings = get_settings()
read_url = settings.database_read_url.get_secret_value()
read_engine = create_engine(
    read_url, pool_pre_ping=True, pool_recycle=1800, hide_parameters=True,
    isolation_level='READ COMMITTED',
    connect_args={'connect_timeout': 2, 'read_timeout': math.ceil(settings.database_replica_wait_seconds) + 1,
                  'write_timeout': 2},
) if read_url else None
ReadSessionLocal = sessionmaker(bind=read_engine, autoflush=False, expire_on_commit=False) if read_engine else None


@contextmanager
def catalog_session(primary):
    """Use the replica only after it applies the master's current committed GTID.

    The replica account must have SELECT only. Auth, write transactions, events,
    Alembic and collectors retain SessionLocal, which always targets the master.
    """
    if ReadSessionLocal is None:
        yield primary
        return
    # A master failure must propagate, not be mistaken for a replica problem.
    position = primary.scalar(text('SELECT @@GLOBAL.gtid_binlog_pos'))
    if not position:
        yield primary
        return
    with ReadSessionLocal() as replica:
        try:
            applied = replica.scalar(text('SELECT MASTER_GTID_WAIT(:position, :timeout)'),
                                     {'position': position, 'timeout': settings.database_replica_wait_seconds})
            if applied != 0:
                replica.rollback()
                selected = primary
            else:
                selected = replica
        except SQLAlchemyError as exc:
            replica.rollback()
            logging.getLogger('culturepick.db').warning('Replica unavailable; catalog uses master (%s)', type(exc).__name__)
            selected = primary
        try:
            yield selected
        finally:
            # Never commit writes from a read connection.
            replica.rollback()


def get_db():
    with SessionLocal() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
