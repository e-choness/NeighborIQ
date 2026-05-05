"""
Celery application configuration for scraper-service.

The scraper-service Celery worker handles:
  - run_scraper: Launches a Scrapy spider for a given set of cities
  - Celery Beat schedule: nightly crawl at 02:00

The ai-insights-service has its own Celery app that consumes
the 'insights' queue — no direct coupling between the two services.
"""
import os

from celery import Celery
from celery.schedules import crontab

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/2")

app = Celery("scraper_worker", broker=BROKER_URL)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,
    task_routes={
        "scraper.tasks.run_scraper": {"queue": "scraper"},
    },
    beat_schedule={
        "nightly-scrape": {
            "task": "scraper.tasks.run_scraper",
            "schedule": crontab(hour=2, minute=0),
            "kwargs": {"cities": ["toronto", "vancouver", "calgary"]},
        }
    },
    timezone="Asia/Shanghai",
)

# Auto-discover tasks in this package
app.autodiscover_tasks(["tasks"])
