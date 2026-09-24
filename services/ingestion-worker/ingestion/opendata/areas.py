"""
Neighbourhood boundaries (GeoJSON) → od_areas, and point-in-polygon assignment.

Every other open-data layer is summarised per area, and listings/properties get
an area_id, so this loader runs first for each city.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


_TRAILING_CODE = re.compile(r"\s*\(\d+\)\s*$")


def normalize_area_name(name: str | None) -> str | None:
    """Toronto publishes names like "Annex (95)"; other datasets say "Annex"."""
    if not name:
        return None
    return _TRAILING_CODE.sub("", str(name)).strip() or None


def read_features(path: Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if data.get("type") != "FeatureCollection":
        raise ValueError(f"{path}: expected a GeoJSON FeatureCollection")
    return data["features"]


def feature_name(props: dict, name_fields: list[str]) -> str | None:
    for field in name_fields:
        for key, value in props.items():
            if key.lower() == field.lower() and value not in (None, ""):
                return str(value).strip()
    return None


def load_areas(
    session: Session,
    city: str,
    source: str,
    features: list[dict],
    name_fields: list[str],
    code_fields: list[str] | None = None,
) -> int:
    """Upsert polygons by (city, name). Returns the number of areas written."""
    written = 0
    for feature in features:
        props = feature.get("properties") or {}
        name = normalize_area_name(feature_name(props, name_fields))
        geometry = feature.get("geometry")
        if not name or not geometry or geometry.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        code = feature_name(props, code_fields or [])
        session.execute(
            text("""
                WITH g AS (
                    SELECT ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))) AS geom
                )
                INSERT INTO od_areas (city, name, code, source, geom, latitude, longitude, area_km2)
                SELECT :city, :name, :code, :source,
                       ST_CollectionExtract(g.geom, 3),
                       ST_Y(ST_PointOnSurface(g.geom)), ST_X(ST_PointOnSurface(g.geom)),
                       ST_Area(g.geom::geography) / 1e6
                FROM g
                ON CONFLICT (city, name) DO UPDATE SET
                    code = EXCLUDED.code, source = EXCLUDED.source, geom = EXCLUDED.geom,
                    latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude,
                    area_km2 = EXCLUDED.area_km2, loaded_at = now()
            """),
            {"geojson": json.dumps(geometry), "city": city, "name": name[:255],
             "code": code[:64] if code else None, "source": source},
        )
        written += 1
    assign_areas(session, city)
    return written


_ASSIGN = {
    "house_houses": "latitude IS NOT NULL",
    "od_properties": "latitude IS NOT NULL",
    "od_permits": "latitude IS NOT NULL",
}


def assign_areas(session: Session, city: str) -> None:
    """Point-in-polygon: set area_id on listings, properties and permits in this city."""
    for table, has_point in _ASSIGN.items():
        session.execute(text(f"""
            UPDATE {table} t SET area_id = a.id
            FROM od_areas a
            WHERE LOWER(t.city) = LOWER(:city) AND LOWER(a.city) = LOWER(:city) AND t.{has_point}
              AND ST_Contains(a.geom, ST_SetSRID(ST_MakePoint(t.longitude, t.latitude), 4326))
        """), {"city": city})
    # Properties without coordinates can still match by neighbourhood name
    session.execute(text("""
        UPDATE od_properties p SET area_id = a.id
        FROM od_areas a
        WHERE p.area_id IS NULL AND p.neighbourhood IS NOT NULL
          AND LOWER(p.city) = LOWER(:city) AND LOWER(a.city) = LOWER(:city)
          AND LOWER(a.name) = LOWER(p.neighbourhood)
    """), {"city": city})


def put_stat(session: Session, area_id: int, metric: str, value, source: str, period: str = "") -> None:
    session.execute(
        text("""
            INSERT INTO od_area_stats (area_id, metric, period, value, source)
            VALUES (:area_id, :metric, :period, :value, :source)
            ON CONFLICT (area_id, metric, period) DO UPDATE SET value = EXCLUDED.value, source = EXCLUDED.source
        """),
        {"area_id": area_id, "metric": metric, "period": period,
         "value": float(value) if value is not None else None, "source": source},
    )


def refresh_listing_stats(session: Session, city: str) -> None:
    """Per-area market metrics from listings, so every area layer can be mapped the same way."""
    rows = session.execute(text("""
        SELECT h.area_id,
               COUNT(*) AS n,
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY h.price::numeric / NULLIF(h.sqft, 0)) AS ppsf,
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ry.gross_yield) AS gross_yield
        FROM house_houses h LEFT JOIN house_rental_yields ry ON ry.house_id = h.id
        WHERE h.is_active = 1 AND h.area_id IS NOT NULL AND LOWER(h.city) = LOWER(:city)
        GROUP BY h.area_id
    """), {"city": city}).fetchall()
    for r in rows:
        put_stat(session, r.area_id, "listings_active", r.n, "listings")
        put_stat(session, r.area_id, "listings_median_ppsf", r.ppsf, "listings")
        if r.gross_yield is not None:
            put_stat(session, r.area_id, "listings_median_gross_yield_pct", float(r.gross_yield) * 100, "listings")
