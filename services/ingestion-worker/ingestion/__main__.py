"""
Ingestion CLI.

  python -m ingestion seed [--per-neighbourhood 25] [--cities Toronto,Calgary]
  python -m ingestion import FILE.json|FILE.csv [--source partner]
  python -m ingestion rents [data/reference/rent_benchmarks.csv]
  python -m ingestion osm [--cities Toronto,...]
  python -m ingestion bootstrap          # rents + seed (the demo stack's first run)
  python -m ingestion opendata --list | --city Vancouver | --sources a,b [--url U | --file F]

Every listing write goes through canonical.normalize/validate and writer.upsert_listings,
then enqueues ai_insights.tasks.compute_insights for the affected houses.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ingestion import benchmarks, canonical, osm, seed, writer
from shared.database.sync import sync_database_url

logger = logging.getLogger("ingestion")

DATABASE_URL = sync_database_url()
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/2")
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parents[1] / "data"))


def _session():
    return sessionmaker(bind=create_engine(DATABASE_URL, pool_pre_ping=True))()


def dispatch_insights(house_ids: list[int]) -> None:
    """Fire-and-forget: ask the ai-insights worker to (re)compute these listings."""
    if not house_ids:
        return
    from celery import Celery

    app = Celery("ingestion_dispatch", broker=BROKER_URL)
    try:
        app.send_task(
            "ai_insights.tasks.compute_insights", kwargs={"house_ids": house_ids}, queue="insights"
        )
    except Exception:
        logger.exception("Could not enqueue compute_insights — run it later from the admin page")
    finally:
        app.close()


def ingest(items: list[dict], dispatch: bool = True) -> dict:
    """Normalize, validate and upsert listings. Returns a summary."""
    accepted, rejected = [], []
    for raw in items:
        item = canonical.normalize(raw)
        errors = canonical.validate(item)
        if errors:
            rejected.append({"url": item.get("url"), "errors": errors})
        else:
            accepted.append(item)

    session = _session()
    try:
        ids = writer.upsert_listings(session, accepted)
        communities = writer.refresh_communities(session)
        _assign_areas(session, {item["city"] for item in accepted})
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    if dispatch:
        dispatch_insights(ids)
    for r in rejected[:20]:
        logger.warning("Rejected %s: %s", r["url"], "; ".join(r["errors"]))
    return {"accepted": len(ids), "rejected": len(rejected), "communities": communities}


def _assign_areas(session, cities: set[str]) -> None:
    """Attach listings to neighbourhood polygons when open-data boundaries are loaded."""
    from sqlalchemy import text

    from ingestion.opendata.areas import assign_areas

    loaded = {
        r[0].lower()
        for r in session.execute(text("SELECT DISTINCT city FROM od_areas"))
    } if session.execute(text("SELECT to_regclass('od_areas')")).scalar() else set()
    for city in cities:
        if city.lower() in loaded:
            assign_areas(session, city)


def run_opendata(keys: list[str], url: str | None = None, file: str | None = None) -> list[dict]:
    from ingestion.opendata.runner import load_source

    session = _session()
    try:
        return [load_source(session, key, url=url, file=file) for key in keys]
    finally:
        session.close()


def read_file(path: Path, source: str) -> list[dict]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data["listings"] if isinstance(data, dict) else data
    elif path.suffix.lower() == ".csv":
        with open(path, newline="", encoding="utf-8") as fh:
            items = list(csv.DictReader(fh))
    else:
        raise ValueError(f"Unsupported file type: {path.suffix} (use .json or .csv)")
    for item in items:
        item.setdefault("source", source)
    return items


def load_rents(path: Path) -> int:
    session = _session()
    try:
        n = benchmarks.load(session, benchmarks.read_csv(path))
        session.commit()
        return n
    finally:
        session.close()


def load_osm(cities: list[str]) -> list[dict]:
    results = []
    session = _session()
    try:
        for city in cities:
            try:
                results.append(osm.load_city(session, city))
                session.commit()
            except Exception as exc:  # network errors, Overpass rate limits
                session.rollback()
                logger.exception("OSM load failed for %s", city)
                results.append({"city": city, "error": str(exc)})
    finally:
        session.close()
    return results


def _listing_count() -> int:
    from sqlalchemy import text

    session = _session()
    try:
        return session.execute(text("SELECT COUNT(*) FROM house_houses")).scalar() or 0
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="python -m ingestion")
    sub = parser.add_subparsers(dest="command", required=True)

    p_seed = sub.add_parser("seed", help="Load deterministic synthetic demo listings")
    p_seed.add_argument("--per-neighbourhood", type=int, default=25)
    p_seed.add_argument("--cities", default="")

    p_import = sub.add_parser("import", help="Import listings from a canonical JSON or CSV file")
    p_import.add_argument("path", type=Path)
    p_import.add_argument("--source", default="import")

    p_rents = sub.add_parser("rents", help="Load rent benchmarks CSV")
    p_rents.add_argument("path", type=Path, nargs="?",
                         default=DATA_DIR / "reference" / "rent_benchmarks.csv")

    p_osm = sub.add_parser("osm", help="Load OpenStreetMap POIs and link listings")
    p_osm.add_argument("--cities", default=",".join(c.name for c in seed.CITIES))

    p_od = sub.add_parser("opendata", help="Load public open data (boundaries, assessments, census, transit…)")
    p_od.add_argument("--list", action="store_true", help="show available sources")
    p_od.add_argument("--sources", default="", help="comma-separated source keys")
    p_od.add_argument("--city", default="", help="every source for these comma-separated cities, in dependency order")
    p_od.add_argument("--url", default=None, help="override the download URL (single source)")
    p_od.add_argument("--file", default=None, help="load a local file instead of downloading (single source)")

    p_boot = sub.add_parser("bootstrap", help="rents + seed — first run of the demo stack")
    p_boot.add_argument("--if-empty", action="store_true",
                        help="do nothing when listings already exist (safe on every start)")

    args = parser.parse_args(argv)
    cities = [c.strip() for c in getattr(args, "cities", "").split(",") if c.strip()]

    if args.command == "seed":
        result = ingest(seed.generate_listings(args.per_neighbourhood, cities=cities or None))
    elif args.command == "import":
        result = ingest(read_file(args.path, args.source))
    elif args.command == "rents":
        result = {"benchmarks": load_rents(args.path)}
    elif args.command == "osm":
        result = {"cities": load_osm(cities)}
    elif args.command == "opendata":
        from ingestion.opendata.sources import SOURCES, for_city

        if args.list:
            result = {k: {"city": s.city or "national", "kind": s.kind, "licence": s.licence,
                          "verified": s.verified} for k, s in SOURCES.items()}
        else:
            keys = [k.strip() for k in args.sources.split(",") if k.strip()]
            for city in [c.strip() for c in args.city.split(",") if c.strip()]:
                keys += [s.key for s in for_city(city)]
            unknown = [k for k in keys if k not in SOURCES]
            if unknown or not keys:
                parser.error(f"unknown or missing sources: {unknown or '(none)'} — see --list")
            if (args.url or args.file) and len(keys) != 1:
                parser.error("--url/--file apply to exactly one source")
            result = {"loads": run_opendata(keys, args.url, args.file)}
    elif args.if_empty and _listing_count() > 0:
        result = {"skipped": "listings already present"}
    else:  # bootstrap
        result = {
            "benchmarks": load_rents(DATA_DIR / "reference" / "rent_benchmarks.csv"),
            **ingest(seed.generate_listings()),
        }

    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
