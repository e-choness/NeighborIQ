"""
Integration tests: batch tasks against a seeded PostgreSQL.

Seeds a small, self-contained neighbourhood inside one transaction-scoped
connection and rolls it back afterwards. Skipped when no database is reachable.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from shared.database.sync import sync_database_url

DB_URL = sync_database_url()


@pytest.fixture()
def db():
    engine = create_engine(DB_URL)
    try:
        conn = engine.connect()
        conn.execute(text("SELECT 1 FROM house_rent_benchmarks LIMIT 1"))
    except Exception:
        pytest.skip("PostgreSQL with the NeighborIQ schema is not available")
    conn.rollback()
    trans = conn.begin()
    # Code under test calls session.commit(); savepoints keep it inside our rollback
    session = Session(bind=conn, join_transaction_mode="create_savepoint")
    session.execute(
        text("""
        INSERT INTO house_rent_benchmarks (city, bedrooms, avg_rent, source)
        VALUES ('Apitown', 2, 2400, 'test')
    """)
    )
    ids = []
    for i, (price, sqft) in enumerate(
        [(700000, 800), (720000, 800), (760000, 800), (800000, 800), (840000, 800), (600000, 800)]
    ):
        ids.append(
            session.execute(
                text("""
            INSERT INTO house_houses (title, community, city, region, property_type, price, sqft,
                area, rooms, property_tax, condo_fee, latitude, longitude, url, is_active,
                status, source, is_synthetic, created_at, updated_at)
            VALUES (:t, 'Testhood', 'Apitown', 'Central', 'condo', :p, :s, 74, 2, 3000, 500,
                    :lat, -79.38, :u, 1, 'active', 'test', 1, NOW(), NOW())
            RETURNING id
        """),
                {"t": f"unit {i}", "p": price, "s": sqft, "lat": 43.65 + i * 0.001, "u": f"test://api/{i}"},
            ).scalar_one()
        )
    yield session, ids
    session.close()
    trans.rollback()
    conn.close()


def test_batch_yields_and_narrative(db):
    from tasks import batch_tasks as bt

    session, ids = db
    bt.compute_insights.run(house_ids=ids, session=session)
    row = session.execute(
        text("SELECT annual_rent, gross_yield, net_yield FROM house_rental_yields WHERE house_id = :id"),
        {"id": ids[-1]},
    ).fetchone()
    assert row.annual_rent == 28800
    assert float(row.gross_yield) == pytest.approx(0.048, abs=1e-4)
    assert 0 < float(row.net_yield) < float(row.gross_yield)

    stats = bt._aggregate_city_stats(session, "Apitown")
    assert stats["listing_count"] == 6 and stats["price_trend_pct"] is None
    assert stats["top_neighborhoods"].startswith("Testhood")


def test_workers_register_their_tasks():
    from tasks.celery_app import app as celery_app

    celery_app.loader.import_default_modules()
    assert "ai_insights.tasks.compute_insights" in celery_app.tasks


def test_recompute_all_fans_out(db, monkeypatch):
    from tasks import batch_tasks as bt

    session, ids = db
    sent = []
    monkeypatch.setattr(bt.compute_insights, "apply_async", lambda kwargs, queue: sent.append(kwargs))
    total = bt.recompute_all.run(session=session, batch_size=4)
    assert total >= 6
    assert sum(len(k["house_ids"]) for k in sent) == total
