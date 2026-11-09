from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True, pool_recycle=1800,
                       connect_args={'connect_timeout': 5}, hide_parameters=True, isolation_level='READ COMMITTED')
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
