"""
Load open-data sources: resolve → download (cached) → parse → summarise per area → log.

    python -m ingestion opendata --list
    python -m ingestion opendata --sources vancouver_areas,vancouver_assessments
    python -m ingestion opendata --city Vancouver
    python -m ingestion opendata --sources census_profile --url https://…/98-401-X2021006_…_CSV.zip
    python -m ingestion opendata --sources toronto_crime --file ./mci.csv
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from ingestion.opendata import areas, assessments, census, gtfs, incidents, indicators, permits
from ingestion.opendata.fetch import download, log_load, open_text
from ingestion.opendata.sources import SOURCES, Source, resolve_url

logger = logging.getLogger(__name__)


def _cities_with_areas(session: Session) -> list[str]:
    return [r[0] for r in session.execute(text("SELECT DISTINCT city FROM od_areas"))]


def _load(session: Session, source: Source, path: Path) -> int:
    opts = source.options
    if source.kind == "areas":
        return areas.load_areas(
            session,
            source.city,
            source.key,
            areas.read_features(path),
            opts["name_fields"],
            opts.get("code_fields"),
        )
    if source.kind == "assessments":
        with open_text(path, ".csv") as fh:
            n = assessments.load(session, fh, source.city, source.key, opts["mapping"], opts)
        areas.assign_areas(session, source.city)
        return n
    if source.kind == "permits":
        with open_text(path, ".csv") as fh:
            n = permits.load(session, fh, source.city, source.key, opts["mapping"], opts)
        areas.assign_areas(session, source.city)
        permits.summarise(session, source.city, source.key)
        return n
    if source.kind == "incidents":
        with open_text(path, ".csv") as fh:
            return incidents.load(session, fh, source.city, source.key, opts["mapping"], opts)
    if source.kind == "gtfs":
        n = gtfs.load(session, path, source.city, source.key.removesuffix("_gtfs"))
        gtfs.summarise(session, source.city, source.key)
        return n
    if source.kind == "census_points":
        with open_text(path, opts.get("member"), encoding="latin-1") as fh:
            return census.load_points(session, fh)
    if source.kind == "census_profile":
        with open_text(path, opts.get("member"), encoding="latin-1") as fh:
            n = census.load_profile(session, fh)
        for city in _cities_with_areas(session):
            census.aggregate_to_areas(session, city)
        return n
    if source.kind == "valet":
        return indicators.load_valet(session, indicators.read_json(path), source.key)
    if source.kind == "statcan_table":
        with open_text(path, opts.get("member")) as fh:
            return indicators.load_statcan_table(
                session, fh, opts["series_prefix"], opts["filters"], source=source.key
            )
    raise ValueError(f"Unknown source kind {source.kind}")


def load_source(session: Session, key: str, url: str | None = None, file: str | None = None) -> dict:
    """Load one source in its own transaction; failures are logged, never half-applied."""
    source = SOURCES[key]
    try:
        path = Path(file) if file else download(url or resolve_url(source))
        rows = _load(session, source, path)
        if source.city:
            areas.refresh_listing_stats(session, source.city)
        log_load(session, key, source.licence, "ok", rows, attribution=source.attribution)
        session.commit()
        return {"source": key, "rows": rows, "status": "ok"}
    except Exception as exc:
        session.rollback()
        logger.exception("Open-data load failed: %s", key)
        log_load(
            session,
            key,
            source.licence,
            "error",
            None,
            f"{type(exc).__name__}: {exc}",
            attribution=source.attribution,
        )
        session.commit()
        return {"source": key, "status": "error", "message": str(exc)}
