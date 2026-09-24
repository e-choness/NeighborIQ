"""
Redis-backed URL deduplication pipeline.

Hashes each listing's (url, price, status) and stores it in Redis with a 7-day TTL.
An unchanged listing seen again within the window is dropped; a price or status
change produces a new fingerprint, so it reaches the writer and lands in
house_price_history.
"""

import hashlib
import logging

import redis
from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)


class RedisDedupPipeline:
    """
    Drops items whose (url, price, status) was seen within the last 7 days.
    Uses Redis SET with TTL for O(1) membership check.
    """

    REDIS_KEY_PREFIX = "scraper:dedup:"

    def __init__(self, redis_url: str, ttl_seconds: int):
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.client: redis.Redis | None = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            redis_url=crawler.settings.get("REDIS_URL", "redis://localhost:6379/0"),
            ttl_seconds=crawler.settings.getint("DEDUP_TTL_SECONDS", 7 * 24 * 3600),
        )

    def open_spider(self, spider):
        self.client = redis.from_url(self.redis_url, decode_responses=True)

    def close_spider(self, spider):
        if self.client:
            self.client.close()

    def process_item(self, item, spider):
        url = item.get("url")
        if not url:
            # No URL to dedup on — let through
            return item

        key = self._make_key(url, item.get("price"), item.get("status"))
        if self.client.exists(key):
            raise DropItem(f"Unchanged listing (seen within 7 days): {url}")

        self.client.setex(key, self.ttl_seconds, "1")
        return item

    def _make_key(self, url: str, price=None, status=None) -> str:
        fingerprint = f"{url}|{price}|{status or 'active'}"
        url_hash = hashlib.sha256(fingerprint.encode()).hexdigest()
        return f"{self.REDIS_KEY_PREFIX}{url_hash}"
