"""
Statistics Canada Census of Population → neighbourhood demographics.

Two inputs, both published under the Statistics Canada Open Licence:
  1. Census Profile (comprehensive download, dissemination-area level): long
     format, one row per (geography, characteristic).
  2. Geographic Attribute File: a representative point for every
     dissemination area (DA).

DA values are stored with their point (od_census_points), then aggregated to
each neighbourhood polygon: counts are summed; medians/averages are
population-weighted means of the DA values — an approximation, labelled as such.
"""
from __future__ import annotations

import csv
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ingestion.opendata.areas import put_stat
from ingestion.opendata.tabular import resolve, to_float

# metric -> (Census Profile characteristic name, aggregation)
CHARACTERISTICS: dict[str, tuple[str, str]] = {
    "population": ("Population, 2021", "sum"),
    "households": ("Private households by household size", "sum"),
    "median_household_income": ("Median total income of household in 2020 ($)", "weighted"),
    "renter_households": ("Renter", "sum"),
    "owner_households": ("Owner", "sum"),
    "median_rent_paid": ("Median monthly shelter costs for rented dwellings ($)", "weighted"),
    "median_owner_costs": ("Median monthly shelter costs for owned dwellings ($)", "weighted"),
    "dwellings_apartment_5plus": ("Apartment in a building that has five or more storeys", "sum"),
    "dwellings_single_detached": ("Single-detached house", "sum"),
    "movers_1yr": ("Movers", "sum"),
}

PROFILE_COLUMNS = {
    "geo_level": ["GEO_LEVEL"],
    "geo_code": ["ALT_GEO_CODE", "DGUID"],
    "name": ["CHARACTERISTIC_NAME"],
    "value": ["C1_COUNT_TOTAL"],
}
POINT_COLUMNS = {
    "geo_code": ["DAUID_ADIDU", "DAUID"],
    "latitude": ["DARPLAT_ADLAT", "DARPLAT"],
    "longitude": ["DARPLONG_ADLONG", "DARPLONG"],
}


def load_points(session: Session, fh) -> int:
    reader = csv.DictReader(fh)
    cols = resolve(reader.fieldnames or [], POINT_COLUMNS, POINT_COLUMNS)
    seen, batch = set(), []
    for row in reader:
        code = row[cols["geo_code"]].strip()
        if code in seen:  # the attribute file repeats a DA once per dissemination block
            continue
        seen.add(code)
        lat, lon = to_float(row[cols["latitude"]]), to_float(row[cols["longitude"]])
        if lat is None or lon is None:
            continue
        batch.append({"code": code, "lat": lat, "lon": lon})
        if len(batch) >= 5000:
            _insert_points(session, batch)
            batch = []
    if batch:
        _insert_points(session, batch)
    return len(seen)


def _insert_points(session: Session, batch: list[dict]) -> None:
    session.execute(text("""
        INSERT INTO od_census_points (geo_code, latitude, longitude)
        VALUES (:code, :lat, :lon)
        ON CONFLICT (geo_code) DO UPDATE SET latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude
    """), batch)


def load_profile(session: Session, fh) -> int:
    """Store the selected characteristics per DA (points must be loaded first)."""
    wanted = {name.strip().lower(): metric for metric, (name, _) in CHARACTERISTICS.items()}
    reader = csv.DictReader(fh)
    cols = resolve(reader.fieldnames or [], PROFILE_COLUMNS, PROFILE_COLUMNS)
    values: dict[str, dict] = {}
    for row in reader:
        if row[cols["geo_level"]].strip().lower() != "dissemination area":
            continue
        metric = wanted.get(row[cols["name"]].strip().lower())
        if metric is None:
            continue
        code = row[cols["geo_code"]].strip()[-8:]  # DGUID ends with the 8-digit DAUID
        number = to_float(row[cols["value"]])
        # First occurrence wins: some names (e.g. "Renter") repeat in later tables
        values.setdefault(code, {}).setdefault(metric, number)
    for code, metrics in values.items():
        session.execute(text("""
            UPDATE od_census_points
            SET values = values || CAST(:values AS jsonb), population = COALESCE(:population, population)
            WHERE geo_code = :code
        """), {"code": code, "values": json.dumps(metrics),
               "population": int(metrics["population"]) if metrics.get("population") else None})
    return len(values)


def aggregate_to_areas(session: Session, city: str, source: str = "statcan_census_2021") -> int:
    """Roll DA values up to each neighbourhood polygon in the city."""
    rows = session.execute(text("""
        SELECT a.id AS area_id, c.population, c.values
        FROM od_areas a
        JOIN od_census_points c
          ON ST_Contains(a.geom, ST_SetSRID(ST_MakePoint(c.longitude, c.latitude), 4326))
        WHERE LOWER(a.city) = LOWER(:city)
    """), {"city": city}).fetchall()

    per_area: dict[int, list] = {}
    for r in rows:
        per_area.setdefault(r.area_id, []).append((r.population or 0, r.values or {}))

    for area_id, das in per_area.items():
        for metric, (_, how) in CHARACTERISTICS.items():
            present = [(pop, vals[metric]) for pop, vals in das if vals.get(metric) is not None]
            if not present:
                continue
            if how == "sum":
                value = sum(v for _, v in present)
            else:
                weight = sum(pop for pop, _ in present)
                value = sum(pop * v for pop, v in present) / weight if weight else None
            put_stat(session, area_id, metric, value, source, period="2021")
        renters = sum(v.get("renter_households") or 0 for _, v in das)
        owners = sum(v.get("owner_households") or 0 for _, v in das)
        if renters + owners:
            put_stat(session, area_id, "renter_share_pct", renters / (renters + owners) * 100, source, "2021")
    return len(per_area)
