"""Database connection boundary for the application."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DATABASE_URL

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return the process-wide database engine, creating it on first use."""
    global _engine
    if _engine is None:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL is not configured")
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the session factory bound to the configured engine."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional session that commits on success and rolls back on failure."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency that wraps one request in a database transaction."""
    with session_scope() as session:
        yield session
