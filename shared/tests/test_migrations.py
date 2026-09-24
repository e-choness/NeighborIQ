"""
Phase 2A — PostgreSQL schema migration tests.

Verifies:
- Alembic upgrade head runs without error
- All Phase 1 + Phase 2 tables exist after migration
- PostGIS extension is installed
- Alembic downgrade + upgrade round-trips cleanly

Requires a real PostgreSQL instance (postgres service in docker-compose).
DATABASE_URL env var must point to it.
"""

import os
import subprocess
import sys

import pytest
import sqlalchemy
from sqlalchemy import create_engine, inspect, text

# Sync DATABASE_URL: replace asyncpg with psycopg2 for synchronous Alembic/inspection
# Destructive: defaults to a dedicated database, never the application's own
_async_url = os.environ.get(
    "MIGRATIONS_DATABASE_URL",
    "postgresql+asyncpg://root:root@postgres:5432/neighboriq_migration_test",
)
SYNC_URL = _async_url.replace("postgresql+asyncpg", "postgresql+psycopg2")

ALEMBIC_INI = "/app/migrations/alembic.ini"


def run_alembic(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run an alembic command from the migrations directory."""
    result = subprocess.run(
        ["alembic", "-c", ALEMBIC_INI] + cmd,
        capture_output=True,
        text=True,
        env={**os.environ, "DATABASE_URL": SYNC_URL},
    )
    return result


@pytest.fixture(scope="module")
def sync_engine():
    engine = create_engine(SYNC_URL)
    yield engine
    engine.dispose()


def _ensure_database_exists() -> None:
    """These tests drop the public schema, so they run in their own database."""
    import psycopg2
    from urllib.parse import urlparse

    target = urlparse(SYNC_URL.replace("postgresql+psycopg2://", "postgresql://"))
    admin = psycopg2.connect(target._replace(path="/postgres").geturl())
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target.path.lstrip("/"),))
        if cur.fetchone() is None:
            cur.execute(f'CREATE DATABASE "{target.path.lstrip("/")}"')
    admin.close()


@pytest.fixture(scope="module", autouse=True)
def apply_migrations():
    """Run alembic downgrade base then upgrade head before any test in this module."""
    import psycopg2

    _ensure_database_exists()

    # Wipe the public schema entirely so no pre-existing tables interfere
    # (other test services may have called init_db/create_all outside of Alembic)
    raw_url = SYNC_URL.replace("postgresql+psycopg2://", "postgresql://")
    conn = psycopg2.connect(raw_url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO PUBLIC;")
    cur.close()
    conn.close()

    # Fresh upgrade to head
    up = run_alembic(["upgrade", "head"])
    assert up.returncode == 0, f"upgrade head failed:\n{up.stderr}"


def test_alembic_upgrade_head_succeeds():
    """upgrade head must be idempotent — running it again on an up-to-date DB is a no-op."""
    result = run_alembic(["upgrade", "head"])
    assert result.returncode == 0, f"Second upgrade head failed:\n{result.stderr}"


def test_all_expected_tables_exist(sync_engine):
    """Every table defined in migrations must be present after upgrade head."""
    expected_tables = [
        # Auth domain
        "auth_users",
        "auth_jwt_keys",
        "auth_refresh_tokens",
        # House domain
        "house_houses",
        "house_communities",
        "house_price_history",
        "house_schools",
        "house_hospitals",
        "house_bus_stops",
        "house_school_links",
        "house_hospital_links",
        "house_bus_links",
        # AI domain (migration 002)
        "house_price_predictions",
        "house_rental_yields",
        "house_market_insights",
        # Canadian listing model (migration 003)
        "house_rent_benchmarks",
    ]
    inspector = inspect(sync_engine)
    existing = set(inspector.get_table_names())

    missing = [t for t in expected_tables if t not in existing]
    assert not missing, f"Missing tables after upgrade head: {missing}"


def test_postgis_extension_installed(sync_engine):
    """PostGIS extension must be installed (migration 002)."""
    with sync_engine.connect() as conn:
        result = conn.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'postgis'")
        )
        row = result.fetchone()
    assert row is not None, "PostGIS extension is not installed"


def test_house_houses_indexes(sync_engine):
    """Critical indexes on house_houses must exist."""
    inspector = inspect(sync_engine)
    indexes = {idx["name"] for idx in inspector.get_indexes("house_houses")}
    required = {
        "idx_house_houses_city_region",
        "idx_house_houses_price",
        "idx_house_houses_location",
        "idx_house_houses_composite",
    }
    missing = required - indexes
    assert not missing, f"Missing indexes on house_houses: {missing}"


def test_canadian_listing_columns(sync_engine):
    """Migration 003 must add the columns valuation and cash flow depend on."""
    inspector = inspect(sync_engine)
    columns = {c["name"] for c in inspector.get_columns("house_houses")}
    required = {
        "property_type", "sqft", "bathrooms", "parking", "postal_code",
        "condo_fee", "property_tax", "status", "listed_at", "source", "is_synthetic",
    }
    missing = required - columns
    assert not missing, f"Missing Canadian listing columns: {missing}"


def test_alembic_schema_matches_orm(sync_engine):
    """create_all (used at service startup) and Alembic must agree on columns."""
    from shared.database.postgres import Base
    import shared.models  # noqa: F401 — registers every table on Base.metadata

    inspector = inspect(sync_engine)
    drift = {}
    for table in Base.metadata.sorted_tables:
        if table.name not in inspector.get_table_names():
            drift[table.name] = "missing table"
            continue
        db_cols = {c["name"] for c in inspector.get_columns(table.name)}
        orm_cols = {c.name for c in table.columns}
        if orm_cols - db_cols:
            drift[table.name] = sorted(orm_cols - db_cols)
    assert not drift, f"ORM columns missing from Alembic schema: {drift}"


def test_alembic_downgrade_base_succeeds():
    """downgrade base must remove all Alembic-managed tables without error."""
    result = run_alembic(["downgrade", "base"])
    assert result.returncode == 0, f"downgrade base failed:\n{result.stderr}"

    # Re-apply so subsequent tests (if any) still have a working schema
    up = run_alembic(["upgrade", "head"])
    assert up.returncode == 0
