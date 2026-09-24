"""
Integration tests: insights endpoints and batch tasks against a seeded PostgreSQL.

Seeds a small, self-contained neighbourhood inside one transaction-scoped
connection and rolls it back afterwards. Skipped when no database is reachable.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.main import app, get_db

DB_URL = os.getenv("SCRAPER_DATABASE_URL", "postgresql://root:root@postgres:5432/house_discovery")


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
    session.execute(text("""
        INSERT INTO house_rent_benchmarks (city, bedrooms, avg_rent, source)
        VALUES ('Apitown', 2, 2400, 'test')
    """))
    ids = []
    for i, (price, sqft) in enumerate([(700000, 800), (720000, 800), (760000, 800),
                                       (800000, 800), (840000, 800), (600000, 800)]):
        ids.append(session.execute(text("""
            INSERT INTO house_houses (title, community, city, region, property_type, price, sqft,
                area, rooms, property_tax, condo_fee, latitude, longitude, url, is_active,
                status, source, is_synthetic, created_at, updated_at)
            VALUES (:t, 'Testhood', 'Apitown', 'Central', 'condo', :p, :s, 74, 2, 3000, 500,
                    :lat, -79.38, :u, 1, 'active', 'test', 1, NOW(), NOW())
            RETURNING id
        """), {"t": f"unit {i}", "p": price, "s": sqft, "lat": 43.65 + i * 0.001,
               "u": f"test://api/{i}"}).scalar_one())
    yield session, ids
    session.close()
    trans.rollback()
    conn.close()


@pytest.fixture()
def client(db):
    session, _ = db
    app.dependency_overrides[get_db] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_insights_bundle(client, db):
    _, ids = db
    subject = ids[-1]  # $600k where comps sit at $875–1050/sqft
    body = client.get(f"/api/v1/houses/{subject}/insights").json()

    v = body["valuation"]
    assert v["verdict"] == "below" and len(v["comps"]) == 5
    assert subject not in {c["house_id"] for c in v["comps"]}
    assert body["rent"]["monthly_rent"] == 2400
    cf = body["cash_flow"]
    assert cf["inputs"]["condo_fee_monthly"] == 500
    assert cf["result"]["gross_yield_pct"] == pytest.approx(2400 * 12 / 600000 * 100, abs=0.01)
    assert body["is_synthetic"] is True
    assert body["ml"] is None  # disabled by default
    # Legacy flat fields come from the valuation — never a fabricated confidence
    assert body["predicted_price"] == v["fair_value"] and body["confidence"] is None


def test_valuation_endpoint_and_404(client, db):
    _, ids = db
    assert client.get(f"/api/v1/houses/{ids[0]}/valuation").json()["method"] == "comps-v1"
    assert client.get("/api/v1/houses/999999999/insights").status_code == 404


def test_cashflow_endpoint(client):
    r = client.post("/api/v1/cashflow", json={"price": 500000, "monthly_rent": 2600})
    assert r.status_code == 200 and "monthly_cash_flow" in r.json()
    assert client.post("/api/v1/cashflow", json={"price": -1, "monthly_rent": 1}).status_code == 422


def test_neighbourhood_analysis_real_stats(client, db):
    body = client.get("/api/v1/neighborhoods/Apitown/Central/analysis").json()
    assert body["listing_count"] == 6
    assert body["median_price"] == 740000
    assert body["market_summary"] is None


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
