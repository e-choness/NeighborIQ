"""Worker wiring."""


def test_worker_registers_its_tasks():
    """autodiscover_tasks(["tasks"]) silently registered nothing — guard the include list."""
    from tasks.celery_app import app as celery_app

    celery_app.loader.import_default_modules()
    assert {"scraper.tasks.run_feed", "scraper.tasks.run_ingestion"} <= set(celery_app.tasks)


def test_run_ingestion_rejects_unknown_commands():
    import pytest

    from tasks.scraper_tasks import run_ingestion

    with pytest.raises(ValueError):
        run_ingestion.run(command="drop-tables")
