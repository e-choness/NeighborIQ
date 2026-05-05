"""
Rate-limit middleware with consecutive-failure alerting.

Tracks consecutive download failures per spider. After FAILURE_ALERT_THRESHOLD
back-to-back failures it logs a CRITICAL alert (wired to external alerting later).
"""
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Tracks consecutive failures and emits a CRITICAL log when the threshold is hit.
    Scrapy's built-in AutoThrottle handles the actual rate limiting.
    """

    def __init__(self, threshold: int):
        self.threshold = threshold
        self._consecutive_failures: dict[str, int] = {}

    @classmethod
    def from_crawler(cls, crawler):
        threshold = crawler.settings.getint("FAILURE_ALERT_THRESHOLD", 10)
        return cls(threshold=threshold)

    def process_response(self, request, response, spider):
        if response.status >= 400:
            self._record_failure(spider.name, request.url)
        else:
            self._reset(spider.name)
        return response

    def process_exception(self, request, exception, spider):
        self._record_failure(spider.name, request.url)

    def _record_failure(self, spider_name: str, url: str):
        count = self._consecutive_failures.get(spider_name, 0) + 1
        self._consecutive_failures[spider_name] = count
        logger.warning("Consecutive failure #%d for spider '%s' on %s", count, spider_name, url)
        if count >= self.threshold:
            logger.critical(
                "ALERT: Spider '%s' has hit %d consecutive failures. "
                "Last failed URL: %s. Manual inspection required.",
                spider_name,
                count,
                url,
            )

    def _reset(self, spider_name: str):
        self._consecutive_failures[spider_name] = 0
