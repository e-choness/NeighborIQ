"""
Insights and market endpoints against a seeded PostgreSQL.

Seeds a small, self-contained neighbourhood inside one transaction-scoped
connection and rolls it back afterwards. Skipped when no database is reachable.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.main import app
from shared.database.sync import get_sync_db

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
    app.dependency_overrides[get_sync_db] = lambda: session
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


def test_markets_summary_and_points(client, db):
    summary = [m for m in client.get("/api/v1/markets").json() if m["city"] == "Apitown"]
    assert summary and summary[0]["listing_count"] == 6
    assert summary[0]["median_price"] == 740000
    assert summary[0]["synthetic_share_pct"] == 100.0

    points = client.get("/api/v1/markets/Apitown/points").json()
    assert points["columns"][:3] == ["id", "lat", "lon"]
    assert len(points["rows"]) == 6
    row = dict(zip(points["columns"], points["rows"][0]))
    assert row["price_per_sqft"] == 875


def test_fabricated_provider_stubs_removed(client):
    """The old /ai/predict stub returned made-up prices; it must stay gone."""
    assert client.post("/api/v1/ai/predict", json={}).status_code == 404


def test_ad_hoc_valuation_and_rents(client, db):
    body = client.post("/api/v1/valuation", json={
        "city": "Apitown", "price": 650000, "sqft": 800, "latitude": 43.652, "longitude": -79.38,
        "property_type": "condo", "rooms": 2,
    }).json()
    assert body["method"] == "comps-v1" and len(body["comps"]) == 6  # all six seeded listings

    assert client.get("/api/v1/rents", params={"city": "apitown", "bedrooms": 2}).json()["monthly_rent"] == 2400
    assert client.get("/api/v1/rents", params={"city": "nowhere", "bedrooms": 2}).json() is None


def test_cashflow_defaults(client):
    body = client.get("/api/v1/cashflow/defaults").json()
    assert body["inputs"]["down_payment_pct"] == 20 and "price" not in body["inputs"]
