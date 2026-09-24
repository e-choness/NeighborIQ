"""
Celery application configuration for the ingestion-worker.

The ingestion-worker handles:
  - run_feed:      crawls a partner listing feed (canonical JSON/CSV) with Scrapy
  - run_ingestion: runs an ingestion CLI command (seed, rents, osm, bootstrap, opendata)
  - Celery Beat:   daily Bank of Canada rates, weekly OSM POI refresh; partner feeds are scheduled only when
                   LISTING_FEED_URL is configured

The insights-worker has its own Celery app that consumes
the 'insights' queue — no direct coupling between the two services.
"""

import os

from celery import Celery
from celery.schedules import crontab

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/2")
LISTING_FEED_URL = os.getenv("LISTING_FEED_URL", "")

# Explicit include: autodiscover_tasks(["tasks"]) would look for a non-existent tasks.tasks module
app = Celery("scraper_worker", broker=BROKER_URL, include=["tasks.scraper_tasks"])

beat_schedule = {
    "daily-rates": {
        "task": "scraper.tasks.run_ingestion",
        "schedule": crontab(hour=6, minute=15),
        "kwargs": {"command": "opendata", "sources": ["bank_of_canada"]},
    },
    "weekly-osm-refresh": {
        "task": "scraper.tasks.run_ingestion",
        "schedule": crontab(hour=3, minute=30, day_of_week="sunday"),
        "kwargs": {"command": "osm"},
    },
}
if LISTING_FEED_URL:
    beat_schedule["nightly-feed"] = {
        "task": "scraper.tasks.run_feed",
        "schedule": crontab(hour=2, minute=0),
        "kwargs": {"feed_url": LISTING_FEED_URL},
    }

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,
    task_routes={
        "scraper.tasks.run_feed": {"queue": "scraper"},
        "scraper.tasks.run_ingestion": {"queue": "scraper"},
    },
    beat_schedule=beat_schedule,
    timezone="America/Toronto",
    # Scrapy runs on Twisted, whose reactor cannot be restarted in-process:
    # give every crawl a fresh worker process.
    worker_max_tasks_per_child=1,
)
