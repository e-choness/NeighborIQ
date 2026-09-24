"""
Synchronous SQLAlchemy engine for code that is not async: Celery workers and the
analytics endpoints (valuation/cash flow), which FastAPI runs in a threadpool.

Derived from the same DATABASE_URL the async engine uses, so one setting
configures every process.
"""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def sync_database_url() -> str:
    url = os.getenv("DATABASE_URL", "postgresql+asyncpg://root:root@localhost:5432/house_discovery")
    return url.replace("+asyncpg", "+psycopg2")


engine = create_engine(sync_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_sync_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a sync session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
