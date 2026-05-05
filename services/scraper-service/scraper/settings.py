"""
Scrapy project settings for NeighborIQ house scraper.
"""
import os

BOT_NAME = "neighboriq_scraper"

SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

# Respectful crawl delay (seconds between requests per domain)
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True  # Actual delay: 0.5*DELAY to 1.5*DELAY

# Concurrency limits — stay polite
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# Obey robots.txt
ROBOTSTXT_OBEY = True

# Middleware ordering
DOWNLOADER_MIDDLEWARES = {
    "scraper.middlewares.useragent.RotatingUserAgentMiddleware": 400,
    "scraper.middlewares.ratelimit.RateLimitMiddleware": 500,
    # Disable built-in user-agent middleware
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
}

# Pipeline ordering (lower number = runs first)
ITEM_PIPELINES = {
    "scraper.pipelines.dedup.RedisDedupPipeline": 100,
    "scraper.pipelines.validation.ValidationPipeline": 200,
    "scraper.pipelines.postgres.PostgresBatchPipeline": 400,
    "scraper.pipelines.celery_dispatch.CeleryDispatchPipeline": 500,
}

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# PostgreSQL connection (sync — Scrapy is synchronous)
DATABASE_URL = os.getenv(
    "SCRAPER_DATABASE_URL",
    "postgresql://root:root@localhost:5432/house_discovery",
)

# Celery broker
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/2")

# Batch size for PostgreSQL insert
POSTGRES_BATCH_SIZE = int(os.getenv("POSTGRES_BATCH_SIZE", "50"))

# Consecutive failure threshold — alert after this many back-to-back failures
FAILURE_ALERT_THRESHOLD = int(os.getenv("FAILURE_ALERT_THRESHOLD", "10"))

# Dedup TTL in seconds (7 days)
DEDUP_TTL_SECONDS = 7 * 24 * 3600

# Logging
LOG_LEVEL = os.getenv("SCRAPY_LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
