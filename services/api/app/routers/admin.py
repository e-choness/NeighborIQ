"""
Operator endpoints (role=admin): trigger ingestion and insight jobs on the
Celery workers, and report data coverage and component health.
"""

import os
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlparse

from celery import Celery
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.security import admin_user
from shared import get_db

router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(admin_user)])

# Send-only Celery client; the workers run in their own containers.
_celery = Celery("api_dispatch", broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/2"))
_celery.conf.update(task_serializer="json", accept_content=["json"])

# Feed URLs are fetched by the ingestion worker — only https hosts listed here are
# allowed, so an admin session cannot be used to probe the internal network (SSRF).
FEED_ALLOWED_HOSTS = {h.strip().lower() for h in os.getenv("FEED_ALLOWED_HOSTS", "").split(",") if h.strip()}

IngestCommand = Literal["seed", "rents", "osm", "bootstrap", "opendata"]


class IngestRequest(BaseModel):
    command: IngestCommand
    cities: list[str] = []
    sources: list[str] = []  # open-data source keys, for command="opendata"


class FeedRequest(BaseModel):
    feed_url: str
    source: str = "feed"


class JobResponse(BaseModel):
    job_id: str
    task: str
    queued_at: datetime


def _enqueue(task: str, kwargs: dict, queue: str) -> JobResponse:
    try:
        result = _celery.send_task(task, kwargs=kwargs, queue=queue)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Could not enqueue job: {exc}") from exc
    return JobResponse(job_id=result.id, task=task, queued_at=datetime.now(UTC))


@router.post("/ingest", response_model=JobResponse)
def trigger_ingestion(request: IngestRequest):
    """Load seed listings, rent benchmarks, OSM POIs or open-data sources."""
    return _enqueue(
        "scraper.tasks.run_ingestion",
        {"command": request.command, "cities": request.cities, "sources": request.sources},
        "scraper",
    )


@router.post("/feeds", response_model=JobResponse)
def trigger_feed(request: FeedRequest):
    """Crawl a licensed partner listing feed (canonical JSON/CSV)."""
    parsed = urlparse(request.feed_url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in FEED_ALLOWED_HOSTS:
        raise HTTPException(
            status_code=422, detail="feed_url must be https and its host listed in FEED_ALLOWED_HOSTS"
        )
    return _enqueue(
        "scraper.tasks.run_feed", {"feed_url": request.feed_url, "source": request.source}, "scraper"
    )


@router.post("/insights/recompute", response_model=JobResponse)
def recompute_insights():
    """Recompute yields/predictions for every active listing."""
    return _enqueue("ai_insights.tasks.recompute_all", {}, "insights")


@router.post("/insights/retrain", response_model=JobResponse)
def retrain_model():
    return _enqueue("ai_insights.tasks.retrain_model", {}, "insights")


_COVERAGE = {
    "listings": "SELECT COUNT(*) FROM house_houses WHERE is_active = 1",
    "synthetic_listings": "SELECT COUNT(*) FROM house_houses WHERE is_active = 1 AND is_synthetic = 1",
    "properties": "SELECT COUNT(*) FROM od_properties",
    "neighbourhood_boundaries": "SELECT COUNT(*) FROM od_areas",
    "census_areas": "SELECT COUNT(*) FROM od_area_stats",
    "rent_benchmarks": "SELECT COUNT(*) FROM house_rent_benchmarks",
    "schools": "SELECT COUNT(*) FROM house_schools",
    "transit_stops": "SELECT COUNT(*) FROM house_bus_stops",
    "rental_yields": "SELECT COUNT(*) FROM house_rental_yields",
}


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)):
    """Row counts per data set, open-data load history, and worker reachability."""
    coverage = {}
    for key, sql in _COVERAGE.items():
        try:
            coverage[key] = (await db.execute(text(sql))).scalar()
        except Exception:
            await db.rollback()
            coverage[key] = None  # table not migrated yet
    try:
        loads = (
            (
                await db.execute(
                    text("""
            SELECT source, loaded_at, row_count, licence, status, message
            FROM od_load_log ORDER BY loaded_at DESC LIMIT 50
        """)
                )
            )
            .mappings()
            .all()
        )
    except Exception:
        await db.rollback()
        loads = []
    try:
        workers = _celery.control.ping(timeout=1.0) or []
        broker = "up"
    except Exception:
        workers, broker = [], "down"
    return {
        "coverage": coverage,
        "open_data_loads": [dict(r) for r in loads],
        "broker": broker,
        "workers": sorted(name for reply in workers for name in reply),
    }
