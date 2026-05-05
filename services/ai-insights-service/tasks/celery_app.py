"""
Celery application for ai-insights-service worker (Phase 5D).

Queues:
  insights   — compute_insights tasks (triggered by scraper after batch insert)
  narratives — generate_daily_narratives (Celery Beat, nightly)

Beat schedule:
  - generate_daily_narratives: runs at 04:00 daily (after scraper nightly run at 02:00)
  - retrain_model: runs weekly (Sunday 03:00)
"""
import os
from celery import Celery
from celery.schedules import crontab

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/2")

app = Celery("ai_insights_worker", broker=BROKER_URL)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,
    task_routes={
        "ai_insights.tasks.compute_insights": {"queue": "insights"},
        "ai_insights.tasks.generate_daily_narratives": {"queue": "narratives"},
        "ai_insights.tasks.retrain_model": {"queue": "insights"},
    },
    beat_schedule={
        "daily-narratives": {
            "task": "ai_insights.tasks.generate_daily_narratives",
            "schedule": crontab(hour=4, minute=0),
            "kwargs": {"cities": ["toronto", "vancouver", "calgary", "ottawa", "montreal"]},
        },
        "weekly-model-retrain": {
            "task": "ai_insights.tasks.retrain_model",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Sunday 03:00
        },
    },
    timezone="America/Toronto",
)

app.autodiscover_tasks(["tasks"])
