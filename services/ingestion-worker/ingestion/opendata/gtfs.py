"""
GTFS static feeds → transit stops with weekday service frequency.

Frequency matters more than proximity: a stop with 400 departures a day is a
different amenity from one with 12. For every stop we count scheduled
departures on a representative weekday (services running on Wednesday per
calendar.txt), keep the highest-capacity mode serving it, and link listings to
their nearest stops.
"""
from __future__ import annotations

import csv
import io
import zipfile
from collections import Counter
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from ingestion.osm import Poi, link_listings

# GTFS route_type (incl. common extended types) → mode, ordered by capacity
_MODE = {0: "streetcar", 1: "subway", 2: "rail", 3: "bus", 4: "ferry", 5: "streetcar",
         11: "bus", 12: "rail", 100: "rail", 109: "rail", 400: "subway", 401: "subway",
         700: "bus", 702: "bus", 900: "streetcar"}
_RANK = {"subway": 0, "rail": 1, "streetcar": 2, "ferry": 3, "bus": 4}


def _read(archive: zipfile.ZipFile, name: str):
    member = next((n for n in archive.namelist() if n.rsplit("/", 1)[-1] == name), None)
    if member is None:
        return None
    return csv.DictReader(io.TextIOWrapper(archive.open(member), encoding="utf-8-sig"))


def weekday_services(archive: zipfile.ZipFile) -> set[str] | None:
    calendar = _read(archive, "calendar.txt")
    if calendar is None:
        return None  # calendar_dates-only feed: count every trip
    return {row["service_id"] for row in calendar if row.get("wednesday") == "1"}


def parse(path: Path) -> list[dict]:
    """Stops with name, coordinates, mode and weekday departures."""
    archive = zipfile.ZipFile(path)
    route_mode = {r["route_id"]: _MODE.get(int(r.get("route_type") or 3), "bus") for r in _read(archive, "routes.txt")}
    services = weekday_services(archive)
    trip_mode = {
        t["trip_id"]: route_mode.get(t["route_id"], "bus")
        for t in _read(archive, "trips.txt")
        if services is None or t["service_id"] in services
    }

    departures: Counter = Counter()
    stop_mode: dict[str, str] = {}
    for st in _read(archive, "stop_times.txt"):
        mode = trip_mode.get(st["trip_id"])
        if mode is None:
            continue
        stop_id = st["stop_id"]
        departures[stop_id] += 1
        current = stop_mode.get(stop_id)
        if current is None or _RANK[mode] < _RANK[current]:
            stop_mode[stop_id] = mode

    stops = []
    for s in _read(archive, "stops.txt"):
        if s.get("location_type") not in (None, "", "0"):
            continue  # stations/entrances: their platforms carry the departures
        try:
            lat, lon = float(s["stop_lat"]), float(s["stop_lon"])
        except (KeyError, ValueError):
            continue
        stops.append({
            "stop_id": s["stop_id"], "name": s.get("stop_name") or s["stop_id"],
            "lat": lat, "lon": lon,
            "mode": stop_mode.get(s["stop_id"], "bus"),
            "departures": departures.get(s["stop_id"], 0),
        })
    return stops


def load(session: Session, path: Path, city: str, feed: str) -> int:
    stops = parse(path)
    pois, ids = [], {}
    for s in stops:
        external_id = f"gtfs:{feed}:{s['stop_id']}"[:64]
        row_id = session.execute(text("""
            INSERT INTO house_bus_stops (name, city, latitude, longitude, mode, osm_id, weekday_departures, created_at)
            VALUES (:name, :city, :lat, :lon, :mode, :ext, :dep, NOW())
            ON CONFLICT (osm_id) DO UPDATE SET
                name = EXCLUDED.name, latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude,
                mode = EXCLUDED.mode, weekday_departures = EXCLUDED.weekday_departures
            RETURNING id
        """), {"name": s["name"][:255], "city": city, "lat": s["lat"], "lon": s["lon"],
               "mode": s["mode"], "ext": external_id, "dep": s["departures"]}).scalar_one()
        ids[external_id] = row_id
        pois.append(Poi(external_id, "transit", s["name"], s["lat"], s["lon"], s["mode"]))

    # Link listings to the nearest stops (replaces OSM transit links for this city)
    link_listings(session, city, pois, ids, categories=("transit",))
    return len(stops)


def summarise(session: Session, city: str, source: str) -> None:
    """Weekday departures per km² — transit intensity per neighbourhood."""
    from ingestion.opendata.areas import put_stat

    for r in session.execute(text("""
        SELECT a.id, a.area_km2, COALESCE(SUM(b.weekday_departures), 0) AS departures
        FROM od_areas a
        LEFT JOIN house_bus_stops b
          ON ST_Contains(a.geom, ST_SetSRID(ST_MakePoint(b.longitude, b.latitude), 4326))
        WHERE LOWER(a.city) = LOWER(:city)
        GROUP BY a.id, a.area_km2
    """), {"city": city}):
        if r.area_km2:
            put_stat(session, r.id, "transit_departures_per_km2", float(r.departures) / r.area_km2, source)
