"""
Normalise DATABASE_URL for each driver.

Hosting platforms hand out plain libpq URLs, e.g. DigitalOcean App Platform:
``postgresql://user:pass@host:25060/db?sslmode=require``. The API needs asyncpg
(``postgresql+asyncpg://``), which takes ``ssl`` instead of ``sslmode``; the
workers and Alembic need psycopg2, which takes ``sslmode``. Either form of
the setting works everywhere.
"""

import os

from sqlalchemy.engine import URL, make_url

DEFAULT = "postgresql+asyncpg://root:root@localhost:5432/house_discovery"


def _raw() -> str:
    return os.getenv("DATABASE_URL") or DEFAULT


def _parse(url: str) -> URL:
    # SQLAlchemy doesn't accept the legacy "postgres://" scheme
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return make_url(url)


def _rename(query: dict, old: str, new: str) -> dict:
    query = dict(query)
    if old in query and new not in query:
        query[new] = query.pop(old)
    else:
        query.pop(old, None)
    return query


def _render(url: URL) -> str:
    # str(URL) masks the password; callers need the real connection string
    return url.render_as_string(hide_password=False)


def async_database_url(url: str | None = None) -> str:
    """For SQLAlchemy's asyncpg driver (the API)."""
    parsed = _parse(url or _raw())
    return _render(parsed.set(drivername="postgresql+asyncpg", query=_rename(parsed.query, "sslmode", "ssl")))


def sync_database_url(url: str | None = None) -> str:
    """For psycopg2 (Celery workers, Scrapy pipelines, Alembic, sync API endpoints)."""
    parsed = _parse(url or _raw())
    return _render(
        parsed.set(drivername="postgresql+psycopg2", query=_rename(parsed.query, "ssl", "sslmode"))
    )
