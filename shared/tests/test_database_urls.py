"""DATABASE_URL in any common form yields the right URL for each driver."""

import pytest

from shared.database.urls import async_database_url, sync_database_url

DO = "postgresql://doadmin:s3cr%40t@db-pg.ondigitalocean.com:25060/defaultdb?sslmode=require"


@pytest.mark.parametrize(
    "given",
    [
        DO,
        DO.replace("postgresql://", "postgres://", 1),
        DO.replace("postgresql://", "postgresql+asyncpg://", 1),
    ],
)
def test_managed_platform_urls(given):
    assert async_database_url(given) == (
        "postgresql+asyncpg://doadmin:s3cr%40t@db-pg.ondigitalocean.com:25060/defaultdb?ssl=require"
    )
    assert sync_database_url(given) == (
        "postgresql+psycopg2://doadmin:s3cr%40t@db-pg.ondigitalocean.com:25060/defaultdb?sslmode=require"
    )


def test_asyncpg_ssl_parameter_becomes_sslmode_for_psycopg2():
    url = "postgresql+asyncpg://u:p@h:5432/d?ssl=verify-full"
    assert sync_database_url(url) == "postgresql+psycopg2://u:p@h:5432/d?sslmode=verify-full"
    assert async_database_url(url) == url


def test_local_default_unchanged():
    url = "postgresql+asyncpg://root:root@postgres:5432/house_discovery"
    assert async_database_url(url) == url
    assert sync_database_url(url) == "postgresql+psycopg2://root:root@postgres:5432/house_discovery"


def test_password_is_not_masked():
    assert "***" not in sync_database_url("postgresql://u:hunter2@h/d")
