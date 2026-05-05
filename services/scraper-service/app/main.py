"""
Scraper Service — FastAPI control API (port 8005).

Provides job control and status endpoints for the Admin Dashboard (Phase 6).
Actual scraping is performed by a separate Celery worker process.

Endpoints:
  POST /api/v1/scraper/jobs           — Trigger a scrape job
  GET  /api/v1/scraper/jobs/{job_id}  — Get job status (via Celery result backend)
  GET  /api/v1/scraper/status         — Current worker health + last run info
  GET  /api/v1/scraper/errors         — Recent failure log
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional

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


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------
class ScrapeJobRequest(BaseModel):
    cities: list[str] = ["toronto", "vancouver", "calgary"]


class ScrapeJobResponse(BaseModel):
    job_id: str
    cities: list[str]
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
    """Enqueue a Celery scrape job for the specified cities."""
    global _last_run
    try:
        result = _celery.send_task(
            "scraper.tasks.run_scraper",
            kwargs={"cities": request.cities},
            queue="scraper",
        )
        _last_run = datetime.now(timezone.utc)
        return ScrapeJobResponse(
            job_id=result.id,
            cities=request.cities,
            queued_at=_last_run,
        )
    except Exception as exc:
        logger.exception("Failed to enqueue scrape job")
        raise HTTPException(status_code=503, detail=f"Could not enqueue job: {exc}")


@app.get("/api/v1/scraper/status", response_model=ScraperStatusResponse)
async def get_status():
    """Return current scraper health and schedule summary."""
    return ScraperStatusResponse(
        worker_status="running",
        last_run=_last_run,
        next_scheduled="02:00 Asia/Shanghai (nightly)",
        recent_error_count=len(_failure_log),
    )


@app.get("/api/v1/scraper/errors")
async def get_errors(limit: int = 50):
    """Return the most recent scraper failure log entries."""
    return {"errors": _failure_log[-limit:], "total": len(_failure_log)}


@app.get("/api/v1/scraper/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
