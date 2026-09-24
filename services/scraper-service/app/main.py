"""
Scraper Service — FastAPI control API (port 8005).

Provides ingestion control and status endpoints for the Admin Dashboard.
Work is performed by a separate Celery worker process. The gateway restricts
every /api/v1/scraper/* route to role=admin.

Endpoints:
  POST /api/v1/scraper/jobs    — Crawl a partner listing feed (allow-listed hosts only)
  POST /api/v1/scraper/ingest  — Run an ingestion command: seed | rents | osm | bootstrap
  GET  /api/v1/scraper/status  — Current worker health + last run info
  GET  /api/v1/scraper/errors  — Recent failure log
"""
import logging
import os
from datetime import datetime, timezone
from typing import Literal, Optional
from urllib.parse import urlparse

from celery import Celery
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="Scraper Service", version="1.0.0")

# ---------------------------------------------------------------------------
# Celery client — send-only; the actual worker runs in a separate container
# ---------------------------------------------------------------------------
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/2")
_celery = Celery("scraper_api_client", broker=BROKER_URL)
_celery.conf.update(task_serializer="json", accept_content=["json"])

# ---------------------------------------------------------------------------
# In-memory failure log (MVP — replace with DB-backed log for production)
# ---------------------------------------------------------------------------
_failure_log: list[dict] = []
_last_run: Optional[datetime] = None

# Feed URLs are fetched by the worker — only https hosts listed here are allowed,
# so an admin session cannot be used to probe the internal network (SSRF).
FEED_ALLOWED_HOSTS = {
    h.strip().lower() for h in os.getenv("FEED_ALLOWED_HOSTS", "").split(",") if h.strip()
}


def _check_feed_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in FEED_ALLOWED_HOSTS:
        raise HTTPException(
            status_code=422,
            detail="feed_url must be https and its host listed in FEED_ALLOWED_HOSTS",
        )


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------
class ScrapeJobRequest(BaseModel):
    feed_url: str
    source: str = "feed"


class ScrapeJobResponse(BaseModel):
    job_id: str
    feed_url: str
    queued_at: datetime


class IngestRequest(BaseModel):
    command: Literal["seed", "rents", "osm", "bootstrap"]
    cities: list[str] = []


class IngestResponse(BaseModel):
    job_id: str
    command: str
    queued_at: datetime


class ScraperStatusResponse(BaseModel):
    worker_status: str
    last_run: Optional[datetime]
    next_scheduled: str
    recent_error_count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/v1/scraper/jobs", response_model=ScrapeJobResponse)
async def trigger_scrape(request: ScrapeJobRequest):
    """Enqueue a crawl of a partner listing feed."""
    _check_feed_url(request.feed_url)
    result = _enqueue(
        "scraper.tasks.run_feed", {"feed_url": request.feed_url, "source": request.source}
    )
    return ScrapeJobResponse(job_id=result.id, feed_url=request.feed_url, queued_at=_last_run)


@app.post("/api/v1/scraper/ingest", response_model=IngestResponse)
async def trigger_ingestion(request: IngestRequest):
    """Enqueue seed / rent-benchmark / OSM loading on the worker."""
    result = _enqueue(
        "scraper.tasks.run_ingestion", {"command": request.command, "cities": request.cities}
    )
    return IngestResponse(job_id=result.id, command=request.command, queued_at=_last_run)


def _enqueue(task: str, kwargs: dict):
    global _last_run
    try:
        result = _celery.send_task(task, kwargs=kwargs, queue="scraper")
    except Exception as exc:
        logger.exception("Failed to enqueue %s", task)
        raise HTTPException(status_code=503, detail=f"Could not enqueue job: {exc}")
    _last_run = datetime.now(timezone.utc)
    return result


@app.get("/api/v1/scraper/status", response_model=ScraperStatusResponse)
async def get_status():
    """Return current scraper health and schedule summary."""
    return ScraperStatusResponse(
        worker_status="running",
        last_run=_last_run,
        next_scheduled="OSM refresh Sundays 03:30 America/Toronto" + (
            "; feed nightly 02:00" if os.getenv("LISTING_FEED_URL") else ""
        ),
        recent_error_count=len(_failure_log),
    )


@app.get("/api/v1/scraper/errors")
async def get_errors(limit: int = 50):
    """Return the most recent scraper failure log entries."""
    return {"errors": _failure_log[-limit:], "total": len(_failure_log)}


@app.get("/health")
@app.get("/api/v1/scraper/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
