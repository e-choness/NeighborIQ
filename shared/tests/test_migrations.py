"""
Alembic migrations against a real PostgreSQL + PostGIS.

Verifies:
- upgrade head runs, and is a no-op when repeated
- every table, key column and foreign key the ORM declares exists
- deleting a listing cascades to its dependent rows
- databases migrated before the squash (at 005_open_data) are adopted
- downgrade base + upgrade head round-trips cleanly

Requires a real PostgreSQL instance (postgres service in docker-compose).
DATABASE_URL env var must point to it.
"""

import os
import subprocess

import pytest
from sqlalchemy import create_engine, inspect, text

# Sync DATABASE_URL: replace asyncpg with psycopg2 for synchronous Alembic/inspection
# Destructive: defaults to a dedicated database, never the application's own
_async_url = os.environ.get(
    "MIGRATIONS_DATABASE_URL",
    "postgresql+asyncpg://root:root@postgres:5432/neighboriq_migration_test",
)
SYNC_URL = _async_url.replace("postgresql+asyncpg", "postgresql+psycopg2")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ALEMBIC_INI = os.environ.get("ALEMBIC_INI", os.path.join(REPO_ROOT, "migrations", "alembic.ini"))


def run_alembic(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run an alembic command from the migrations directory."""
    result = subprocess.run(
        ["alembic", "-c", ALEMBIC_INI] + cmd,
        capture_output=True,
        text=True,
        env={**os.environ, "DATABASE_URL": SYNC_URL},
        cwd=REPO_ROOT,  # alembic.ini's script_location is relative to the repo root
    )
    return result


@pytest.fixture(scope="module")
def sync_engine():
    engine = create_engine(SYNC_URL)
    yield engine
    engine.dispose()


def _ensure_database_exists() -> None:
    """These tests drop the public schema, so they run in their own database."""
    from urllib.parse import urlparse

    import psycopg2

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
    """Every application table is present after upgrade head."""
    expected_tables = {
        "auth_users",
        "auth_jwt_keys",
        "auth_refresh_tokens",
        "house_houses",
        "house_communities",
        "house_price_history",
        "house_schools",
        "house_hospitals",
        "house_bus_stops",
        "house_school_links",
        "house_hospital_links",
        "house_bus_links",
        "house_price_predictions",
        "house_rental_yields",
        "house_market_insights",
        "house_rent_benchmarks",
        "portfolio_saved_houses",
        "od_areas",
        "od_area_stats",
        "od_census_points",
        "od_properties",
        "od_permits",
        "od_indicators",
        "od_load_log",
    }
    missing = expected_tables - set(inspect(sync_engine).get_table_names())
    assert not missing, f"Missing tables after upgrade head: {missing}"


def test_postgis_extension_installed(sync_engine):
    with sync_engine.connect() as conn:
        row = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'postgis'")).fetchone()
    assert row is not None, "PostGIS extension is not installed"


def test_house_houses_indexes(sync_engine):
    """Indexes the listing search and comparables query rely on."""
    indexes = {idx["name"] for idx in inspect(sync_engine).get_indexes("house_houses")}
    required = {
        "idx_house_houses_url",
        "idx_house_houses_price",
        "idx_house_houses_location",
        "idx_house_houses_composite",
        "idx_house_houses_comps",
    }
    missing = required - indexes
    assert not missing, f"Missing indexes on house_houses: {missing}"


def test_canadian_listing_columns(sync_engine):
    """Columns valuation and cash flow depend on."""
    columns = {c["name"] for c in inspect(sync_engine).get_columns("house_houses")}
    required = {
        "property_type",
        "sqft",
        "bathrooms",
        "parking",
        "postal_code",
        "condo_fee",
        "property_tax",
        "status",
        "listed_at",
        "source",
        "is_synthetic",
        "area_id",
    }
    missing = required - columns
    assert not missing, f"Missing Canadian listing columns: {missing}"


def test_alembic_schema_matches_orm(sync_engine):
    """create_all (tests, throwaway databases) and Alembic must agree on columns and foreign keys."""
    import shared.models  # noqa: F401 — registers every table on Base.metadata
    from shared.database.postgres import Base

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
        db_fks = {
            (tuple(fk["constrained_columns"]), fk["referred_table"])
            for fk in inspector.get_foreign_keys(table.name)
        }
        orm_fks = {((fk.parent.name,), fk.column.table.name) for fk in table.foreign_keys}
        if orm_fks - db_fks:
            drift[f"{table.name} foreign keys"] = sorted(orm_fks - db_fks)
    assert not drift, f"ORM declarations missing from the Alembic schema: {drift}"


def test_unique_email(sync_engine):
    uniques = {tuple(u["column_names"]) for u in inspect(sync_engine).get_unique_constraints("auth_users")}
    assert ("email",) in uniques


def test_deleting_a_listing_cascades(sync_engine):
    """Price history, amenity links and derived rows go with the listing."""
    with sync_engine.begin() as conn:
        house_id = conn.execute(
            text("""
            INSERT INTO house_houses (title, city, region, price, url, is_active)
            VALUES ('cascade test', 'Toronto', 'Old Toronto', 500000, 'test://cascade', 1) RETURNING id
        """)
        ).scalar()
        school_id = conn.execute(
            text("INSERT INTO house_schools (name, city) VALUES ('cascade school', 'Toronto') RETURNING id")
        ).scalar()
        conn.execute(
            text("INSERT INTO house_price_history (house_id, price) VALUES (:h, 510000)"), {"h": house_id}
        )
        conn.execute(
            text("INSERT INTO house_school_links (house_id, school_id, distance_m) VALUES (:h, :s, 300)"),
            {"h": house_id, "s": school_id},
        )
        conn.execute(text("DELETE FROM house_houses WHERE id = :h"), {"h": house_id})
        left = conn.execute(
            text("""
            SELECT (SELECT count(*) FROM house_price_history WHERE house_id = :h)
                 + (SELECT count(*) FROM house_school_links WHERE house_id = :h)
        """),
            {"h": house_id},
        ).scalar()
        conn.execute(text("DELETE FROM house_schools WHERE id = :s"), {"s": school_id})
    assert left == 0


def _set_version(sync_engine, version: str) -> None:
    with sync_engine.begin() as conn:
        conn.execute(text("UPDATE alembic_version SET version_num = :v"), {"v": version})


def test_legacy_database_is_adopted(sync_engine):
    """A database migrated to 005_open_data (same schema as 0001_baseline) upgrades without manual steps."""
    down = run_alembic(["downgrade", "0001_baseline"])
    assert down.returncode == 0, down.stderr
    _set_version(sync_engine, "005_open_data")

    up = run_alembic(["upgrade", "head"])
    assert up.returncode == 0, f"legacy database was not adopted:\n{up.stderr}"
    with sync_engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0002_integrity"


def test_partially_migrated_legacy_database_is_refused(sync_engine):
    _set_version(sync_engine, "003_canadian_listing_model")
    try:
        result = run_alembic(["upgrade", "head"])
        assert result.returncode != 0
        assert "legacy revision 003_canadian_listing_model" in result.stderr
    finally:
        _set_version(sync_engine, "0002_integrity")


def test_alembic_downgrade_base_succeeds(sync_engine):
    """downgrade base removes every Alembic-managed table."""
    result = run_alembic(["downgrade", "base"])
    assert result.returncode == 0, f"downgrade base failed:\n{result.stderr}"
    left = {
        t for t in inspect(sync_engine).get_table_names() if t not in ("spatial_ref_sys", "alembic_version")
    }
    assert not left, f"Tables left after downgrade base: {left}"

    # Re-apply so later tests (if any) still have a working schema
    up = run_alembic(["upgrade", "head"])
    assert up.returncode == 0
