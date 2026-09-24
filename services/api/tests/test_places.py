"""Open-data endpoints and the neighbourhood/rate context in listing insights."""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.main import app
from shared.database.sync import get_sync_db, sync_database_url

SQUARE = {"type": "Polygon", "coordinates": [[[-79.40, 43.60], [-79.39, 43.60], [-79.39, 43.61],
                                              [-79.40, 43.61], [-79.40, 43.60]]]}


@pytest.fixture()
def db():
    engine = create_engine(sync_database_url())
    try:
        conn = engine.connect()
        conn.execute(text("SELECT 1 FROM od_areas LIMIT 1"))
    except Exception:
        pytest.skip("PostgreSQL with migration 005 is not available")
    conn.rollback()
    trans = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint")
    area_id = session.execute(text("""
        INSERT INTO od_areas (city, name, source, geom, latitude, longitude, area_km2)
        VALUES ('Placeville', 'Centre', 'test', ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)), 43.605, -79.395, 0.9)
        RETURNING id
    """), {"g": json.dumps(SQUARE)}).scalar_one()
    session.execute(text("""
        INSERT INTO od_area_stats (area_id, metric, period, value, source) VALUES
          (:a, 'median_household_income', '2021', 91000, 'test'),
          (:a, 'crime_per_1000', '2024', 12.0, 'test'),
          (:a, 'crime_per_1000', '2025', 10.5, 'test')
    """), {"a": area_id})
    session.execute(text("""
        INSERT INTO od_properties (city, source, source_id, address, assessed_value, year_built, tax_levy, area_id)
        VALUES ('Placeville', 'test', 'p1', '12 Queen St', 850000, 1990, 4100, :a),
               ('Placeville', 'test', 'p2', '14 Queen St', 900000, 2000, 4300, :a)
    """), {"a": area_id})
    session.execute(text("""
        INSERT INTO od_indicators (series, date, value, label, unit, source) VALUES
          ('boc:V80691335', '2026-09-01', 6.09, '5-year conventional mortgage', 'percent', 'test'),
          ('boc:V80691335', '2026-08-01', 6.14, '5-year conventional mortgage', 'percent', 'test')
    """))
    session.execute(text("""
        INSERT INTO od_load_log (source, row_count, licence, attribution, status)
        VALUES ('test_areas', 1, 'Test licence', 'Contains test data', 'ok')
    """))
    house_id = session.execute(text("""
        INSERT INTO house_houses (title, community, city, region, property_type, price, sqft, rooms,
            latitude, longitude, url, is_active, status, source, is_synthetic, area_id, created_at, updated_at)
        VALUES ('p', 'Centre', 'Placeville', 'C', 'condo', 600000, 800, 2, 43.605, -79.395,
                'test://places/1', 1, 'active', 'test', 1, :a, now(), now())
        RETURNING id
    """), {"a": area_id}).scalar_one()
    yield session, area_id, house_id
    session.close()
    trans.rollback()
    conn.close()


@pytest.fixture()
def client(db):
    session = db[0]
    app.dependency_overrides[get_sync_db] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_areas_list_uses_latest_period(client, db):
    body = client.get("/api/v1/areas", params={"city": "placeville"}).json()
    [area] = body["items"]
    assert area["name"] == "Centre"
    assert area["stats"]["crime_per_1000"] == {"value": 10.5, "period": "2025"}
    assert "crime_per_1000" in body["metrics"]


def test_areas_geojson(client, db):
    fc = client.get("/api/v1/areas/geojson", params={"city": "Placeville"}).json()
    [feature] = fc["features"]
    assert feature["geometry"]["type"] == "MultiPolygon"
    assert feature["properties"]["median_household_income"] == 91000


def test_area_detail(client, db):
    _, area_id, _ = db
    body = client.get(f"/api/v1/areas/{area_id}").json()
    assert [p["value"] for p in body["series"]["crime_per_1000"]] == [12.0, 10.5]
    assert body["properties"]["median_assessed_value"] == 875000
    assert client.get("/api/v1/areas/999999999").status_code == 404


def test_indicators_latest_and_history(client, db):
    [item] = [i for i in client.get("/api/v1/indicators").json()["items"] if i["series"] == "boc:V80691335"]
    assert item["latest"] == 6.09
    assert [h["value"] for h in item["history"]][-2:] == [6.14, 6.09]


def test_property_lookup(client, db):
    items = client.get("/api/v1/properties/lookup", params={"q": "12 que", "city": "Placeville"}).json()["items"]
    assert [i["address"] for i in items] == ["12 Queen St"]
    assert items[0]["area_name"] == "Centre" and items[0]["tax_levy"] == 4100
    assert client.get("/api/v1/properties/lookup", params={"q": "12"}).status_code == 422  # too short


def test_data_sources(client, db):
    items = client.get("/api/v1/data-sources").json()["items"]
    assert any(i["attribution"] == "Contains test data" for i in items)


def test_listing_insights_carry_area_and_rate(client, db):
    _, _, house_id = db
    body = client.get(f"/api/v1/houses/{house_id}/insights").json()
    assert body["area"]["name"] == "Centre"
    assert body["area"]["stats"]["median_household_income"]["value"] == 91000
    assert body["rate"]["rate_pct"] == 6.09
