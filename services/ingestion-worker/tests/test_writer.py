"""
Integration tests for ingestion.writer against PostgreSQL.

Skipped when no database is reachable (unit-only runs); the Docker test profile
provides one.
"""
import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ingestion.canonical import normalize
from ingestion.writer import refresh_communities, upsert_listings

from shared.database.sync import sync_database_url

DB_URL = sync_database_url()


@pytest.fixture()
def session():
    engine = create_engine(DB_URL, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM house_houses LIMIT 1"))
    except Exception:
        pytest.skip("PostgreSQL with the NeighborIQ schema is not available")
    s = sessionmaker(bind=engine)()
    yield s
    s.rollback()  # every test runs inside one rolled-back transaction
    s.close()


def _listing(price: int, **extra) -> dict:
    return normalize({
        "url": "test://writer/1", "title": "t", "city": "Testville", "region": "R",
        "community": "Writer Test", "price": price, "sqft": 800, "rooms": 2,
        "listed_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
        **extra,
    })


def _history(session, house_id):
    return session.execute(
        text("SELECT price FROM house_price_history WHERE house_id = :id ORDER BY recorded_at, id"),
        {"id": house_id},
    ).scalars().all()


def test_insert_records_first_price(session):
    [house_id] = upsert_listings(session, [_listing(800000)])
    assert _history(session, house_id) == [800000]


def test_unchanged_price_adds_no_history(session):
    [house_id] = upsert_listings(session, [_listing(800000)])
    upsert_listings(session, [_listing(800000)])
    assert _history(session, house_id) == [800000]


def test_price_change_appends_history_and_updates_row(session):
    [house_id] = upsert_listings(session, [_listing(800000)])
    [same_id] = upsert_listings(session, [_listing(775000)])
    assert same_id == house_id
    assert _history(session, house_id) == [800000, 775000]
    price = session.execute(text("SELECT price FROM house_houses WHERE id = :id"), {"id": house_id}).scalar()
    assert price == 775000


def test_supplied_history_loaded_on_first_insert(session):
    listed = datetime.now(timezone.utc) - timedelta(days=40)
    item = _listing(
        750000,
        price_history=[
            {"price": 799000, "recorded_at": listed.isoformat()},
            {"price": 750000, "recorded_at": (listed + timedelta(days=20)).isoformat()},
        ],
    )
    [house_id] = upsert_listings(session, [item])
    assert _history(session, house_id) == [799000, 750000]


def test_refresh_communities_aggregates(session):
    upsert_listings(session, [_listing(800000)])
    refresh_communities(session)
    row = session.execute(
        text("SELECT house_count, min_price FROM house_communities WHERE name = 'Writer Test'")
    ).fetchone()
    assert row.house_count == 1 and row.min_price == 800000


def test_refresh_communities_keeps_ids_stable(session):
    upsert_listings(session, [_listing(800000)])
    refresh_communities(session)
    first = session.execute(text("SELECT id FROM house_communities WHERE name = 'Writer Test'")).scalar()
    upsert_listings(session, [_listing(790000)])
    refresh_communities(session)
    row = session.execute(
        text("SELECT id, min_price FROM house_communities WHERE name = 'Writer Test'")
    ).fetchone()
    assert row.id == first and row.min_price == 790000
