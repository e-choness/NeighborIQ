"""
Police-reported incidents → counts per area, category and year (od_area_stats),
plus a rate per 1,000 residents when census population is loaded.

Only aggregates are stored: individual incident records are not needed by the
app and are more sensitive than the totals.
"""
from __future__ import annotations

from collections import Counter

from sqlalchemy import text
from sqlalchemy.orm import Session

from ingestion.opendata.areas import normalize_area_name, put_stat
from ingestion.opendata.tabular import rows, slug, to_float, to_int

REQUIRED = ("category", "year")


def load(session: Session, fh, city: str, source: str, mapping: dict, options: dict | None = None) -> int:
    """Count incidents by (area, category, year). Areas come from coordinates or an area-name column."""
    areas = {
        name.lower(): area_id
        for area_id, name in session.execute(
            text("SELECT id, name FROM od_areas WHERE LOWER(city) = LOWER(:city)"), {"city": city}
        )
    }
    counts: Counter = Counter()
    points: list[tuple[float, float, str, str]] = []
    total = 0
    for raw in rows(fh, mapping, REQUIRED):
        year, category = raw.get("year"), slug(raw.get("category") or "other")
        if not year:
            continue
        total += 1
        name = (normalize_area_name(raw.get("area_name")) or "").lower()
        if name and name in areas:
            counts[(areas[name], category, year)] += 1
            continue
        lat, lon = to_float(raw.get("latitude")), to_float(raw.get("longitude"))
        if lat and lon and 41 < lat < 84:
            points.append((lon, lat, category, year))

    # Coordinates → polygons in the database, in chunks
    for i in range(0, len(points), 5000):
        chunk = points[i:i + 5000]
        result = session.execute(text("""
            SELECT a.id, p.category, p.year, COUNT(*) AS n
            FROM unnest(CAST(:lons AS float8[]), CAST(:lats AS float8[]),
                        CAST(:cats AS text[]), CAST(:years AS text[])) AS p(lon, lat, category, year)
            JOIN od_areas a ON LOWER(a.city) = LOWER(:city)
             AND ST_Contains(a.geom, ST_SetSRID(ST_MakePoint(p.lon, p.lat), 4326))
            GROUP BY a.id, p.category, p.year
        """), {"lons": [p[0] for p in chunk], "lats": [p[1] for p in chunk],
               "cats": [p[2] for p in chunk], "years": [p[3] for p in chunk], "city": city})
        for r in result:
            counts[(r.id, r.category, r.year)] += r.n

    totals: Counter = Counter()
    for (area_id, category, year), n in counts.items():
        put_stat(session, area_id, f"crime_{category}", n, source, period=str(year))
        totals[(area_id, str(year))] += n
    for (area_id, year), n in totals.items():
        put_stat(session, area_id, "crime_total", n, source, period=year)
        population = session.execute(text("""
            SELECT value FROM od_area_stats WHERE area_id = :a AND metric = 'population' ORDER BY period DESC LIMIT 1
        """), {"a": area_id}).scalar()
        if population:
            put_stat(session, area_id, "crime_per_1000", n / population * 1000, source, period=year)
    return total
