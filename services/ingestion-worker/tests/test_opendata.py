"""
Open-data loaders against PostgreSQL + PostGIS, with small fixtures in each
source's published format. Every test runs in a rolled-back transaction.
"""
import csv
import io
import json
import zipfile
from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ingestion.opendata import areas, assessments, census, gtfs, incidents, indicators, permits
from ingestion.opendata import runner
from ingestion.opendata.sources import SOURCES, Source, for_city
from ingestion.opendata.tabular import SchemaError, to_date, to_float
from shared.database.sync import sync_database_url

CITY = "Testopolis"


def _square(lon0, lat0, size=0.01):
    ring = [[lon0, lat0], [lon0 + size, lat0], [lon0 + size, lat0 + size], [lon0, lat0 + size], [lon0, lat0]]
    return {"type": "Polygon", "coordinates": [ring]}


FEATURES = [
    {"type": "Feature", "properties": {"AREA_NAME": "Alpha (1)", "AREA_SHORT_CODE": "1"},
     "geometry": _square(-79.40, 43.60)},
    {"type": "Feature", "properties": {"AREA_NAME": "Beta (2)", "AREA_SHORT_CODE": "2"},
     "geometry": _square(-79.39, 43.60)},
    {"type": "Feature", "properties": {"AREA_NAME": None}, "geometry": _square(0, 0)},  # skipped
]


@pytest.fixture()
def db():
    engine = create_engine(sync_database_url())
    try:
        conn = engine.connect()
        conn.execute(text("SELECT 1 FROM od_areas LIMIT 1"))
    except Exception:
        pytest.skip("PostgreSQL with migration 005 (PostGIS) is not available")
    conn.rollback()
    trans = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    trans.rollback()
    conn.close()


@pytest.fixture()
def city(db):
    assert areas.load_areas(db, CITY, "test_areas", FEATURES, ["AREA_NAME"], ["AREA_SHORT_CODE"]) == 2
    return {name: area_id for area_id, name in db.execute(
        text("SELECT id, name FROM od_areas WHERE city = :c"), {"c": CITY})}


def _stat(db, area_id, metric, period=""):
    return db.execute(text(
        "SELECT value FROM od_area_stats WHERE area_id = :a AND metric = :m AND period = :p"
    ), {"a": area_id, "m": metric, "p": period}).scalar()


def _csv(rows: list[dict]) -> io.StringIO:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return buf


# ── helpers ────────────────────────────────────────────────────────────────

def test_number_and_date_parsing():
    assert to_float("$1,234,500") == 1234500
    assert to_float("") is None and to_float("n/a") is None
    assert to_date("2024-03-15T10:00:00") == date(2024, 3, 15)
    assert to_date("03/15/2024") == date(2024, 3, 15)
    assert to_date("garbage") is None


def test_normalize_area_name():
    assert areas.normalize_area_name("Annex (95)") == "Annex"
    assert areas.normalize_area_name("Plateau-Mont-Royal") == "Plateau-Mont-Royal"


def test_schema_error_names_available_columns():
    fh = _csv([{"WRONG": "1"}])
    with pytest.raises(SchemaError, match="WRONG"):
        list(assessments.rows(fh, {"source_id": ["PID"]}, ["source_id"]))


def test_registry_is_consistent():
    kinds = {"areas", "assessments", "permits", "incidents", "gtfs",
             "census_points", "census_profile", "valet", "statcan_table"}
    for key, source in SOURCES.items():
        assert source.kind in kinds, key
        assert source.licence and source.attribution, key
        if source.kind in ("assessments", "permits", "incidents"):
            assert "source_id" in source.options["mapping"] or source.kind == "incidents", key
    # areas load before anything that is summarised per area
    assert for_city("Vancouver")[0].kind == "areas"


# ── areas ──────────────────────────────────────────────────────────────────

def test_areas_loaded_with_centroid_and_size(db, city):
    assert set(city) == {"Alpha", "Beta"}  # "(1)" suffix stripped
    row = db.execute(text("SELECT latitude, longitude, area_km2 FROM od_areas WHERE id = :i"),
                     {"i": city["Alpha"]}).fetchone()
    assert 43.60 < row.latitude < 43.61 and -79.40 < row.longitude < -79.39
    assert 0.8 < row.area_km2 < 1.0  # 0.01° × 0.01° at 43.6°N ≈ 0.89 km²


def test_listings_assigned_to_areas(db, city):
    house_id = db.execute(text("""
        INSERT INTO house_houses (title, community, city, region, price, sqft, latitude, longitude,
                                  url, is_active, status, source, is_synthetic, created_at, updated_at)
        VALUES ('t', 'x', :c, 'r', 500000, 700, 43.605, -79.385, 'test://od/1', 1, 'active', 'test', 1, now(), now())
        RETURNING id
    """), {"c": CITY}).scalar_one()
    areas.assign_areas(db, CITY)
    assert db.execute(text("SELECT area_id FROM house_houses WHERE id = :i"), {"i": house_id}).scalar() == city["Beta"]


# ── assessments ────────────────────────────────────────────────────────────

VANCOUVER_MAPPING = SOURCES["vancouver_assessments"].options["mapping"]


def test_assessments_vancouver_format(db, city):
    fh = _csv([
        {"pid": "001-001", "from_civic_number": "100", "street_name": "MAIN ST", "property_postal_code": "v5t3a1",
         "legal_type": "STRATA", "zoning_district": "RM-4", "current_land_value": "700000",
         "current_improvement_value": "300000", "year_built": "1998", "tax_levy": "3100",
         "tax_assessment_year": "2025", "geo_point_2d": "43.6050, -79.3950"},
        # an older roll year for the same property must not overwrite the newer one
        {"pid": "001-001", "from_civic_number": "100", "street_name": "MAIN ST", "property_postal_code": "v5t3a1",
         "legal_type": "STRATA", "zoning_district": "RM-4", "current_land_value": "600000",
         "current_improvement_value": "250000", "year_built": "1998", "tax_levy": "2900",
         "tax_assessment_year": "2024", "geo_point_2d": "43.6050, -79.3950"},
    ])
    assert assessments.load(db, fh, CITY, "test_assess", VANCOUVER_MAPPING) == 2
    areas.assign_areas(db, CITY)
    row = db.execute(text("SELECT * FROM od_properties WHERE source = 'test_assess'")).mappings().one()
    assert row["address"] == "100 MAIN ST" and row["postal_code"] == "V5T 3A1"
    assert row["assessed_value"] == 1_000_000 and row["assessment_year"] == 2025
    assert row["area_id"] == city["Alpha"]


def test_assessments_match_area_by_neighbourhood_name(db, city):
    fh = _csv([{"roll_number": "9", "address": "1 Test Rd", "assessed_value": "450000", "comm_name": "BETA"}])
    assessments.load(db, fh, CITY, "test_assess2", SOURCES["calgary_assessments"].options["mapping"])
    areas.assign_areas(db, CITY)
    assert db.execute(text("SELECT area_id FROM od_properties WHERE source = 'test_assess2'")).scalar() == city["Beta"]


def test_montreal_floor_area_converted_from_m2(db):
    fh = _csv([{"ID_UEV": "1", "CIVIQUE_DEBUT": "5", "NOM_RUE": "rue X", "SUPERFICIE_BATIMENT": "100",
                "NOMBRE_LOGEMENT": "3", "ANNEE_CONSTRUCTION": "1925"}])
    assessments.load(db, fh, CITY, "test_mtl", SOURCES["montreal_assessments"].options["mapping"], {"areas_in_sqm": True})
    row = db.execute(text("SELECT floor_area_sqft, units FROM od_properties WHERE source = 'test_mtl'")).one()
    assert row.floor_area_sqft == 1076 and row.units == 3


# ── permits ────────────────────────────────────────────────────────────────

def test_permits_summarised_per_area(db, city):
    today = date.today().isoformat()
    fh = _csv([
        {"permitnum": "P1", "issueddate": today, "permitclassmapped": "New", "housingunits": "40",
         "estprojectcost": "12000000", "latitude": "43.605", "longitude": "-79.395"},
        {"permitnum": "P2", "issueddate": "2001-01-01", "permitclassmapped": "New", "housingunits": "10",
         "estprojectcost": "1", "latitude": "43.605", "longitude": "-79.395"},  # outside 24-month window
    ])
    assert permits.load(db, fh, CITY, "test_permits", SOURCES["calgary_permits"].options["mapping"]) == 2
    areas.assign_areas(db, CITY)
    permits.summarise(db, CITY, "test_permits")
    assert _stat(db, city["Alpha"], "permit_units_24m") == 40


# ── incidents ──────────────────────────────────────────────────────────────

def test_incidents_by_name_and_coordinates(db, city):
    areas.put_stat(db, city["Alpha"], "population", 2000, "test", period="2021")
    fh = _csv([
        {"MCI_CATEGORY": "Assault", "OCC_YEAR": "2025", "NEIGHBOURHOOD_158": "Alpha (1)", "LAT_WGS84": "0", "LONG_WGS84": "0"},
        {"MCI_CATEGORY": "Assault", "OCC_YEAR": "2025", "NEIGHBOURHOOD_158": "NSA", "LAT_WGS84": "43.605", "LONG_WGS84": "-79.395"},
        {"MCI_CATEGORY": "Auto Theft", "OCC_YEAR": "2025", "NEIGHBOURHOOD_158": "", "LAT_WGS84": "43.605", "LONG_WGS84": "-79.385"},
    ])
    assert incidents.load(db, fh, CITY, "test_crime", SOURCES["toronto_crime"].options["mapping"]) == 3
    assert _stat(db, city["Alpha"], "crime_assault", "2025") == 2
    assert _stat(db, city["Beta"], "crime_auto_theft", "2025") == 1
    assert _stat(db, city["Alpha"], "crime_per_1000", "2025") == pytest.approx(1.0)


# ── census ─────────────────────────────────────────────────────────────────

def test_census_points_profile_and_area_aggregation(db, city):
    points = _csv([
        {"DAUID_ADIDU": "35200001", "DARPLAT_ADLAT": "43.603", "DARPLONG_ADLONG": "-79.397"},
        {"DAUID_ADIDU": "35200001", "DARPLAT_ADLAT": "43.603", "DARPLONG_ADLONG": "-79.397"},  # repeated per block
        {"DAUID_ADIDU": "35200002", "DARPLAT_ADLAT": "43.607", "DARPLONG_ADLONG": "-79.393"},
    ])
    assert census.load_points(db, points) == 2

    def row(code, name, value):
        return {"GEO_LEVEL": "Dissemination area", "ALT_GEO_CODE": code, "CHARACTERISTIC_NAME": name,
                "C1_COUNT_TOTAL": value}
    profile = _csv([
        row("35200001", "Population, 2021", "600"),
        row("35200002", "Population, 2021", "400"),
        row("35200001", "Median total income of household in 2020 ($)", "80000"),
        row("35200002", "Median total income of household in 2020 ($)", "100000"),
        row("35200001", "Renter", "150"), row("35200001", "Owner", "50"),
        row("35200002", "Renter", "50"), row("35200002", "Owner", "150"),
        {"GEO_LEVEL": "Province", "ALT_GEO_CODE": "35", "CHARACTERISTIC_NAME": "Population, 2021", "C1_COUNT_TOTAL": "1"},
    ])
    assert census.load_profile(db, profile) == 2
    assert census.aggregate_to_areas(db, CITY) == 1
    alpha = city["Alpha"]
    assert _stat(db, alpha, "population", "2021") == 1000
    assert _stat(db, alpha, "median_household_income", "2021") == pytest.approx(88000)  # 0.6×80k + 0.4×100k
    assert _stat(db, alpha, "renter_share_pct", "2021") == pytest.approx(50.0)


# ── GTFS ───────────────────────────────────────────────────────────────────

def _gtfs_zip(tmp_path):
    files = {
        "routes.txt": "route_id,route_type\nL1,1\nB1,3\n",
        "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
                        "WK,1,1,1,1,1,0,0,20250101,20271231\nSAT,0,0,0,0,0,1,0,20250101,20271231\n",
        "trips.txt": "trip_id,route_id,service_id\nT1,L1,WK\nT2,B1,WK\nT3,B1,WK\nT4,B1,SAT\n",
        "stop_times.txt": "trip_id,stop_id,departure_time\nT1,S1,08:00:00\nT2,S1,08:05:00\nT3,S2,08:10:00\nT4,S2,09:00:00\n",
        "stops.txt": "stop_id,stop_name,stop_lat,stop_lon,location_type\n"
                     "S1,Alpha Station,43.605,-79.395,0\nS2,Beta Stop,43.605,-79.385,0\nST,Station Hall,43.605,-79.395,1\n",
    }
    path = tmp_path / "gtfs.zip"
    with zipfile.ZipFile(path, "w") as z:
        for name, body in files.items():
            z.writestr(name, body)
    return path


def test_gtfs_parse_counts_weekday_departures_and_mode(tmp_path):
    stops = {s["stop_id"]: s for s in gtfs.parse(_gtfs_zip(tmp_path))}
    assert set(stops) == {"S1", "S2"}  # parent station skipped
    assert stops["S1"]["departures"] == 2 and stops["S1"]["mode"] == "subway"  # best mode wins
    assert stops["S2"]["departures"] == 1  # Saturday-only trip excluded


def test_gtfs_load_and_density(db, city, tmp_path):
    assert gtfs.load(db, _gtfs_zip(tmp_path), CITY, "testfeed") == 2
    gtfs.summarise(db, CITY, "test_gtfs")
    assert _stat(db, city["Alpha"], "transit_departures_per_km2") > 0


# ── indicators ─────────────────────────────────────────────────────────────

def test_bank_of_canada_valet(db):
    payload = {
        "seriesDetail": {"V80691335": {"label": "5-year conventional mortgage"}},
        "observations": [
            {"d": "2026-09-16", "V80691335": {"v": "6.09"}},
            {"d": "2026-09-09", "V80691335": {"v": ""}},  # missing value skipped
        ],
    }
    assert indicators.load_valet(db, payload) == 1
    row = db.execute(text("SELECT value, label FROM od_indicators WHERE series = 'boc:V80691335'")).one()
    assert row.value == 6.09 and row.label == "5-year conventional mortgage"


def test_statcan_table_filters_dimension(db):
    fh = _csv([
        {"REF_DATE": "2026-07", "GEO": "Toronto, Ontario", "New housing price indexes": "Total (house and land)",
         "UOM": "Index, 201612=100", "VALUE": "118.2"},
        {"REF_DATE": "2026-07", "GEO": "Toronto, Ontario", "New housing price indexes": "House only",
         "UOM": "Index, 201612=100", "VALUE": "130"},
    ])
    indicators.load_statcan_table(db, fh, "nhpi", {"New housing price indexes": "Total (house and land)"})
    row = db.execute(text("SELECT date, value FROM od_indicators WHERE series = 'nhpi:toronto'")).one()
    assert row.date == date(2026, 7, 1) and row.value == 118.2


# ── runner ─────────────────────────────────────────────────────────────────

def test_runner_logs_success_and_failure(db, tmp_path, monkeypatch):
    geojson = tmp_path / "areas.geojson"
    geojson.write_text(json.dumps({"type": "FeatureCollection", "features": FEATURES}))
    monkeypatch.setitem(SOURCES, "test_src", Source(
        "test_src", CITY, "areas", "Test licence", "Test", options={"name_fields": ["AREA_NAME"]}))

    assert runner.load_source(db, "test_src", file=str(geojson))["status"] == "ok"
    bad = runner.load_source(db, "test_src", file=str(tmp_path / "missing.geojson"))
    assert bad["status"] == "error"
    statuses = [r.status for r in db.execute(
        text("SELECT status FROM od_load_log WHERE source = 'test_src' ORDER BY id"))]
    assert statuses == ["ok", "error"]
