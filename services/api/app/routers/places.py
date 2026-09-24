"""
Public open data: neighbourhood areas and their metrics, economic indicators,
assessment-roll property lookup, and data provenance/attribution.

All tables here are loaded by the ingestion worker (ingestion/opendata);
endpoints return empty results — never errors — when a layer is not loaded.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.database.sync import get_sync_db

router = APIRouter(tags=["places"])

# Metrics a client may colour the map by, with how they read
AREA_METRICS = {
    "listings_median_ppsf": "Median asking $/sq ft",
    "listings_median_gross_yield_pct": "Median gross yield %",
    "median_household_income": "Median household income (2020, approx.)",
    "renter_share_pct": "Renter households %",
    "median_rent_paid": "Median rent paid (2021, approx.)",
    "transit_departures_per_km2": "Weekday transit departures / km²",
    "crime_per_1000": "Reported major crime per 1,000 residents",
    "permit_units_24m": "Housing units permitted, last 24 months",
}


def _table_exists(db: Session, name: str) -> bool:
    return bool(db.execute(text("SELECT to_regclass(:t)"), {"t": name}).scalar())


def _latest_stats(db: Session, area_ids: list[int]) -> dict[int, dict]:
    """Latest period per (area, metric)."""
    if not area_ids:
        return {}
    rows = db.execute(
        text("""
        SELECT DISTINCT ON (area_id, metric) area_id, metric, period, value
        FROM od_area_stats WHERE area_id = ANY(:ids)
        ORDER BY area_id, metric, period DESC
    """),
        {"ids": area_ids},
    ).fetchall()
    out: dict[int, dict] = {}
    for r in rows:
        out.setdefault(r.area_id, {})[r.metric] = {"value": r.value, "period": r.period or None}
    return out


@router.get("/api/v1/areas")
def list_areas(city: str, db: Session = Depends(get_sync_db)):
    """Neighbourhoods in a city with their latest metrics (no geometry)."""
    if not _table_exists(db, "od_areas"):
        return {"city": city, "metrics": AREA_METRICS, "items": []}
    rows = (
        db.execute(
            text("""
        SELECT id, name, code, latitude, longitude, area_km2
        FROM od_areas WHERE LOWER(city) = LOWER(:city) ORDER BY name
    """),
            {"city": city},
        )
        .mappings()
        .all()
    )
    stats = _latest_stats(db, [r["id"] for r in rows])
    return {
        "city": city,
        "metrics": AREA_METRICS,
        "items": [{**dict(r), "stats": stats.get(r["id"], {})} for r in rows],
    }


@router.get("/api/v1/areas/geojson")
def areas_geojson(
    city: str,
    tolerance: float = Query(default=0.0002, ge=0, le=0.01, description="Simplification in degrees"),
    db: Session = Depends(get_sync_db),
):
    """Simplified polygons with every latest metric as properties — for choropleths."""
    if not _table_exists(db, "od_areas"):
        return {"type": "FeatureCollection", "features": []}
    rows = db.execute(
        text("""
        SELECT id, name, ST_AsGeoJSON(ST_Multi(ST_SimplifyPreserveTopology(geom, :tol)), 5) AS geometry
        FROM od_areas WHERE LOWER(city) = LOWER(:city)
    """),
        {"city": city, "tol": tolerance},
    ).fetchall()
    stats = _latest_stats(db, [r.id for r in rows])
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": r.id,
                "geometry": json.loads(r.geometry),
                "properties": {
                    "id": r.id,
                    "name": r.name,
                    **{m: s["value"] for m, s in stats.get(r.id, {}).items()},
                },
            }
            for r in rows
        ],
    }


@router.get("/api/v1/areas/{area_id}")
def area_detail(area_id: int, db: Session = Depends(get_sync_db)):
    """Everything known about one neighbourhood: metrics over time, properties, supply."""
    area = (
        db.execute(
            text("""
        SELECT id, city, name, code, latitude, longitude, area_km2 FROM od_areas WHERE id = :id
    """),
            {"id": area_id},
        )
        .mappings()
        .first()
    )
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")

    series: dict[str, list] = {}
    for r in db.execute(
        text("""
        SELECT metric, period, value, source FROM od_area_stats WHERE area_id = :id ORDER BY metric, period
    """),
        {"id": area_id},
    ):
        series.setdefault(r.metric, []).append(
            {"period": r.period or None, "value": r.value, "source": r.source}
        )

    properties = (
        db.execute(
            text("""
        SELECT COUNT(*) AS count,
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY assessed_value) AS median_assessed_value,
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY year_built) AS median_year_built,
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY tax_levy) AS median_tax_levy
        FROM od_properties WHERE area_id = :id
    """),
            {"id": area_id},
        )
        .mappings()
        .first()
    )

    return {
        **dict(area),
        "metrics": AREA_METRICS,
        "series": series,
        "properties": {k: (float(v) if v is not None else None) for k, v in properties.items()},
    }


@router.get("/api/v1/indicators")
def indicators(db: Session = Depends(get_sync_db)):
    """Latest value and last-12-observation history for each loaded series."""
    if not _table_exists(db, "od_indicators"):
        return {"items": []}
    rows = db.execute(
        text("""
        SELECT series, label, unit, source, date, value,
               ROW_NUMBER() OVER (PARTITION BY series ORDER BY date DESC) AS rn
        FROM od_indicators
    """)
    ).fetchall()
    items: dict[str, dict] = {}
    for r in rows:
        if r.rn > 12:
            continue
        item = items.setdefault(
            r.series,
            {"series": r.series, "label": r.label, "unit": r.unit, "source": r.source, "history": []},
        )
        if r.rn == 1:
            item.update(latest=r.value, date=r.date.isoformat())
        item["history"].append({"date": r.date.isoformat(), "value": r.value})
    for item in items.values():
        item["history"].reverse()
    return {"items": sorted(items.values(), key=lambda i: i["series"])}


@router.get("/api/v1/properties/lookup")
def property_lookup(
    q: str = Query(min_length=3, description="Start of a street address"),
    city: Optional[str] = None,
    db: Session = Depends(get_sync_db),
):
    """Assessment-roll facts for an address — pre-fills the deal analyzer."""
    if not _table_exists(db, "od_properties"):
        return {"items": []}
    rows = (
        db.execute(
            text("""
        SELECT p.id, p.city, p.address, p.postal_code, p.latitude, p.longitude, p.property_class,
               p.zoning, p.year_built, p.units, p.floor_area_sqft, p.lot_size_sqft,
               p.assessed_value, p.land_value, p.improvement_value, p.tax_levy, p.assessment_year,
               p.source, a.name AS area_name, a.id AS area_id
        FROM od_properties p LEFT JOIN od_areas a ON a.id = p.area_id
        WHERE LOWER(p.address) LIKE LOWER(:prefix)
          AND (CAST(:city AS TEXT) IS NULL OR LOWER(p.city) = LOWER(:city))
        ORDER BY p.address
        LIMIT 10
    """),
            {"prefix": q.strip() + "%", "city": city},
        )
        .mappings()
        .all()
    )
    return {"items": [dict(r) for r in rows]}


@router.get("/api/v1/data-sources")
def data_sources(db: Session = Depends(get_sync_db)):
    """What public data is loaded, when, and the attribution each licence requires."""
    if not _table_exists(db, "od_load_log"):
        return {"items": []}
    rows = (
        db.execute(
            text("""
        SELECT DISTINCT ON (source) source, loaded_at, row_count, licence, attribution
        FROM od_load_log WHERE status = 'ok'
        ORDER BY source, loaded_at DESC
    """)
        )
        .mappings()
        .all()
    )
    return {"items": [dict(r) for r in rows]}
