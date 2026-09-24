"""
OpenStreetMap points of interest via the Overpass API.

Loads schools, hospitals and transit stops inside the bounding box of each
city's listings, then links every listing to its nearest POIs (distance in
metres) in house_school_links / house_hospital_links / house_bus_links.

Data © OpenStreetMap contributors, ODbL 1.0 — the UI must show attribution
(see NOTICE). Overpass is a shared community service: one query per city,
run on demand or weekly, never per request.
"""
from __future__ import annotations

import json
import logging
import math
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
USER_AGENT = "NeighborIQ/0.2 (+https://github.com/e-choness/neighboriq)"

# How far to look, and how many links to keep per listing, by category
LINK_RULES = {
    "school": {"radius_m": 2000, "keep": 3},
    "hospital": {"radius_m": 5000, "keep": 1},
    "transit": {"radius_m": 1000, "keep": 3},
}

_TABLES = {
    "school": ("house_schools", "house_school_links", "school_id"),
    "hospital": ("house_hospitals", "house_hospital_links", "hospital_id"),
    "transit": ("house_bus_stops", "house_bus_links", "bus_stop_id"),
}


@dataclass(frozen=True)
class Poi:
    osm_id: str
    category: str  # school | hospital | transit
    name: str
    lat: float
    lon: float
    detail: str | None = None  # school level, hospital type, or transit mode


def build_query(south: float, west: float, north: float, east: float) -> str:
    bbox = f"{south},{west},{north},{east}"
    return f"""
[out:json][timeout:180];
(
  nwr["amenity"="school"]({bbox});
  nwr["amenity"="college"]({bbox});
  nwr["amenity"="university"]({bbox});
  nwr["amenity"="hospital"]({bbox});
  node["highway"="bus_stop"]({bbox});
  node["railway"="tram_stop"]({bbox});
  nwr["railway"="station"]({bbox});
  nwr["station"="subway"]({bbox});
);
out center tags;
""".strip()


def _categorize(tags: dict) -> tuple[str, str | None] | None:
    amenity = tags.get("amenity")
    if amenity in ("school", "college", "university"):
        level = (tags.get("isced:level") or "school") if amenity == "school" else amenity
        return "school", level
    if amenity == "hospital":
        return "hospital", tags.get("healthcare:speciality") or "hospital"
    if tags.get("station") == "subway" or tags.get("subway") == "yes":
        return "transit", "subway"
    if tags.get("railway") == "tram_stop":
        return "transit", "streetcar"
    if tags.get("railway") == "station":
        return "transit", "rail"
    if tags.get("highway") == "bus_stop":
        return "transit", "bus"
    return None


def parse_elements(payload: dict) -> list[Poi]:
    """Turn an Overpass JSON response into POIs (unnamed features are skipped)."""
    pois: dict[str, Poi] = {}
    for el in payload.get("elements", []):
        tags = el.get("tags") or {}
        name = tags.get("name")
        category = _categorize(tags)
        if not name or category is None:
            continue
        if "lat" in el:
            lat, lon = el["lat"], el["lon"]
        elif "center" in el:
            lat, lon = el["center"]["lat"], el["center"]["lon"]
        else:
            continue
        osm_id = f"{el['type']}/{el['id']}"
        pois[osm_id] = Poi(osm_id, category[0], name, lat, lon, category[1])
    return list(pois.values())


def fetch(query: str, timeout: int = 200) -> dict:
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — fixed https URL
        return json.loads(resp.read())


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest(
    origin: tuple[float, float], pois: list[Poi], radius_m: float, keep: int
) -> list[tuple[Poi, int]]:
    """The `keep` closest POIs within radius_m of origin, nearest first."""
    lat, lon = origin
    # Cheap bounding-box prefilter before the exact distance
    dlat = radius_m / 111_000
    dlon = radius_m / (111_000 * max(math.cos(math.radians(lat)), 0.01))
    hits = []
    for poi in pois:
        if abs(poi.lat - lat) > dlat or abs(poi.lon - lon) > dlon:
            continue
        d = haversine_m(lat, lon, poi.lat, poi.lon)
        if d <= radius_m:
            hits.append((poi, int(round(d))))
    hits.sort(key=lambda h: h[1])
    return hits[:keep]


def city_bbox(session: Session, city: str, pad: float = 0.02) -> tuple[float, float, float, float] | None:
    row = session.execute(
        text("""
            SELECT MIN(latitude), MIN(longitude), MAX(latitude), MAX(longitude)
            FROM house_houses
            WHERE LOWER(city) = LOWER(:city) AND latitude IS NOT NULL
        """),
        {"city": city},
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return float(row[0]) - pad, float(row[1]) - pad, float(row[2]) + pad, float(row[3]) + pad


def store_pois(session: Session, city: str, pois: list[Poi]) -> dict[str, int]:
    """Upsert POIs by osm_id. Returns {osm_id: row id}."""
    ids: dict[str, int] = {}
    for poi in pois:
        table = _TABLES[poi.category][0]
        detail_col = {"school": "level", "hospital": "hospital_type", "transit": "mode"}[poi.category]
        row_id = session.execute(
            text(f"""
                INSERT INTO {table} (name, city, latitude, longitude, {detail_col}, osm_id, created_at)
                VALUES (:name, :city, :lat, :lon, :detail, :osm_id, NOW())
                ON CONFLICT (osm_id) DO UPDATE SET
                    name = EXCLUDED.name, latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude, {detail_col} = EXCLUDED.{detail_col}
                RETURNING id
            """),
            {"name": poi.name[:255], "city": city, "lat": poi.lat, "lon": poi.lon,
             "detail": (poi.detail or "")[:50], "osm_id": poi.osm_id},
        ).scalar_one()
        ids[poi.osm_id] = row_id
    return ids


def link_listings(session: Session, city: str, pois: list[Poi], poi_ids: dict[str, int]) -> int:
    """Replace this city's listing→POI links with the nearest POIs. Returns links written."""
    houses = session.execute(
        text("""
            SELECT id, latitude, longitude FROM house_houses
            WHERE LOWER(city) = LOWER(:city) AND latitude IS NOT NULL
        """),
        {"city": city},
    ).fetchall()
    by_category: dict[str, list[Poi]] = {}
    for poi in pois:
        by_category.setdefault(poi.category, []).append(poi)

    written = 0
    house_ids = [h.id for h in houses]
    for category, (_, link_table, fk) in _TABLES.items():
        session.execute(
            text(f"DELETE FROM {link_table} WHERE house_id = ANY(:ids)"), {"ids": house_ids}
        )
        rule = LINK_RULES[category]
        candidates = by_category.get(category, [])
        for house in houses:
            origin = (float(house.latitude), float(house.longitude))
            for poi, dist in nearest(origin, candidates, rule["radius_m"], rule["keep"]):
                session.execute(
                    text(f"INSERT INTO {link_table} (house_id, {fk}, distance_m) VALUES (:h, :p, :d)"),
                    {"h": house.id, "p": poi_ids[poi.osm_id], "d": dist},
                )
                written += 1
    return written


def load_city(session: Session, city: str, payload: dict | None = None) -> dict:
    """Fetch (unless payload is given), store and link POIs for one city."""
    bbox = city_bbox(session, city)
    if bbox is None:
        return {"city": city, "skipped": "no geocoded listings"}
    if payload is None:
        logger.info("Querying Overpass for %s bbox=%s", city, bbox)
        payload = fetch(build_query(*bbox))
    pois = parse_elements(payload)
    poi_ids = store_pois(session, city, pois)
    links = link_listings(session, city, pois, poi_ids)
    counts = {c: sum(1 for p in pois if p.category == c) for c in _TABLES}
    return {"city": city, "pois": counts, "links": links}
