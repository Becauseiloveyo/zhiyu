from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from zhiyu.core.config import settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    # Lazy by design: importing the API and serving /health must not require the DB driver/server.
    if make_url(settings.database_url).drivername != "postgresql+psycopg":
        raise ValueError("M1 canonical database requires postgresql+psycopg")
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_timeout=2,
        hide_parameters=True,
        connect_args={
            "connect_timeout": settings.db_connect_timeout,
            "options": f"-c timezone=UTC -c statement_timeout={settings.db_statement_timeout_ms} "
            f"-c lock_timeout={settings.db_lock_timeout_ms}",
        },
    )


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db: Session = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
