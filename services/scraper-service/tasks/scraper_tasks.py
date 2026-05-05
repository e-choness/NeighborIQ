"""
Celery task definitions for the scraper-service worker.

`run_scraper` — triggered by Celery Beat (nightly) or via the FastAPI
                control API. Runs a Scrapy CrawlerProcess for the
                requested cities.
"""
import logging

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from tasks.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="scraper.tasks.run_scraper", bind=True, max_retries=3)
def run_scraper(self, cities: list[str] | None = None):
    """
    Run the Lianjia house spider for the given cities.

    Args:
        cities: List of city subdomain names (e.g., ["nanjing", "beijing"]).
                Defaults to the spider's DEFAULT_CITIES if not provided.

    Retries up to 3 times with exponential backoff on failure.
    """
    import os
    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "scraper.settings")

    settings = get_project_settings()
    process = CrawlerProcess(settings)

    spider_kwargs = {}
    if cities:
        spider_kwargs["cities"] = cities

    try:
        from scraper.spiders.house_spider import LianjiaHouseSpider
        process.crawl(LianjiaHouseSpider, **spider_kwargs)
        process.start()  # Blocks until crawl is complete
        logger.info("Scrape completed for cities: %s", cities)
    except Exception as exc:
        logger.exception("Scraper task failed: %s", exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)
