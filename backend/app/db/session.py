"""Database session dependency for FastAPI."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def _get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=_get_engine()
        )
    return _SessionLocal


def get_session_local():
    """Public accessor for the configured session factory (used by the CLI)."""
    return _get_session_local()


def get_db() -> Session:
    db = _get_session_local()()
    try:
        yield db
    finally:
        db.close()
