"""
Issued building permits → od_permits, summarised per area as new-unit supply.

Investor question: "how much competing supply is coming to this neighbourhood?"
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from ingestion.opendata.areas import put_stat
from ingestion.opendata.tabular import apply_geo_point, rows, to_date, to_float, to_int

REQUIRED = ("source_id",)

_UPSERT = text("""
    INSERT INTO od_permits (city, source, source_id, issued_date, kind, units, value, latitude, longitude)
    VALUES (:city, :source, :source_id, :issued_date, :kind, :units, :value, :latitude, :longitude)
    ON CONFLICT (source, source_id) DO UPDATE SET
        issued_date = EXCLUDED.issued_date, kind = EXCLUDED.kind, units = EXCLUDED.units,
        value = EXCLUDED.value, latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude
""")


def load(session: Session, fh, city: str, source: str, mapping: dict, options: dict | None = None) -> int:
    batch, total = [], 0
    for raw in rows(fh, mapping, REQUIRED):
        apply_geo_point(raw)
        lat, lon = to_float(raw.get("latitude")), to_float(raw.get("longitude"))
        if lat is not None and not (41 < lat < 84):
            lat = lon = None
        batch.append({
            "city": city, "source": source, "source_id": raw["source_id"][:64],
            "issued_date": to_date(raw.get("issued_date")),
            "kind": (raw.get("kind") or None) and raw["kind"][:128],
            "units": to_int(raw.get("units")),
            "value": to_int(raw.get("value")),
            "latitude": lat, "longitude": lon,
        })
        if len(batch) >= 2000:
            session.execute(_UPSERT, batch)
            total += len(batch)
            batch = []
    if batch:
        session.execute(_UPSERT, batch)
        total += len(batch)
    return total


def summarise(session: Session, city: str, source: str, months: int = 24) -> None:
    since = date.today() - timedelta(days=months * 30)
    for r in session.execute(text("""
        SELECT area_id, COUNT(*) AS permits, COALESCE(SUM(units), 0) AS units
        FROM od_permits
        WHERE LOWER(city) = LOWER(:city) AND area_id IS NOT NULL AND issued_date >= :since
        GROUP BY area_id
    """), {"city": city, "since": since}):
        put_stat(session, r.area_id, f"permits_{months}m", r.permits, source)
        put_stat(session, r.area_id, f"permit_units_{months}m", r.units, source)
