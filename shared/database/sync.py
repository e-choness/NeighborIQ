"""
Synchronous SQLAlchemy engine for code that is not async: Celery workers and the
analytics endpoints (valuation/cash flow), which FastAPI runs in a threadpool.

Derived from the same DATABASE_URL the async engine uses, so one setting
configures every process.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from shared.database.urls import sync_database_url

__all__ = ["SessionLocal", "engine", "get_sync_db", "sync_database_url"]


engine = create_engine(sync_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_sync_db() -> Generator[Session]:
    """FastAPI dependency yielding a sync session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
