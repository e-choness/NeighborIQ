"""
Celery task definitions for the ingestion-worker.

run_feed      — crawl a canonical listing feed with Scrapy (ListingFeedSpider)
run_ingestion — run an ingestion CLI command: seed, rents, osm, bootstrap or opendata
"""

import logging
import os

from tasks.celery_app import app

logger = logging.getLogger(__name__)

INGESTION_COMMANDS = {"seed", "rents", "osm", "bootstrap", "opendata"}


@app.task(name="scraper.tasks.run_feed", bind=True, max_retries=3)
def run_feed(self, feed_url: str, source: str = "feed"):
    """Crawl one listing feed. Retries with exponential backoff on failure."""
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    from scraper.spiders.feed_spider import ListingFeedSpider

    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "scraper.settings")
    process = CrawlerProcess(get_project_settings())
    try:
        process.crawl(ListingFeedSpider, feed_url=feed_url, source=source)
        process.start()  # Blocks until the crawl completes
        logger.info("Feed crawl completed: %s", feed_url)
    except Exception as exc:
        logger.exception("Feed crawl failed: %s", exc)
        raise self.retry(exc=exc, countdown=2**self.request.retries * 60) from exc


@app.task(name="scraper.tasks.run_ingestion")
def run_ingestion(command: str, cities: list[str] | None = None, sources: list[str] | None = None):
    """Run `python -m ingestion <command>` inside the worker."""
    if command not in INGESTION_COMMANDS:
        raise ValueError(f"Unknown ingestion command: {command}")
    from ingestion.__main__ import main

    argv = [command]
    if cities and command in ("seed", "osm"):
        argv += ["--cities", ",".join(cities)]
    if command == "opendata":
        if sources:
            argv += ["--sources", ",".join(sources)]
        if cities:
            argv += ["--city", ",".join(cities)]
    return main(argv)
