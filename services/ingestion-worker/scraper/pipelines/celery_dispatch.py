"""
Celery task dispatch pipeline.

After each batch insert, enqueues a `compute_insights` Celery task
for the ai-insights-service worker to process asynchronously.

No direct HTTP call between scraper-service and ai-insights-service.
"""
import logging

from celery import Celery

logger = logging.getLogger(__name__)


def _make_celery_app(broker_url: str) -> Celery:
    app = Celery("scraper_dispatch", broker=broker_url)
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_backend=None,  # Fire-and-forget; no result needed from scraper side
    )
    return app


class CeleryDispatchPipeline:
    """
    Reads inserted_ids from the PostgresBatchPipeline reference and
    enqueues a compute_insights task after each spider run.

    Because pipelines are closed in reverse-declaration order, this runs
    after PostgresBatchPipeline.close_spider has flushed the last batch.
    """

    def __init__(self, broker_url: str):
        self.broker_url = broker_url
        self._celery: Celery | None = None
        self._postgres_pipeline = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            broker_url=crawler.settings.get(
                "CELERY_BROKER_URL", "redis://localhost:6379/2"
            )
        )

    def open_spider(self, spider):
        self._celery = _make_celery_app(self.broker_url)

    def close_spider(self, spider):
        # After PostgresBatchPipeline has flushed, dispatch tasks for all collected IDs
        if self._postgres_pipeline and self._postgres_pipeline.inserted_ids:
            self._dispatch(self._postgres_pipeline.inserted_ids)
        if self._celery:
            self._celery.close()

    def process_item(self, item, spider):
        # Wire up postgres pipeline reference on first item
        if self._postgres_pipeline is None:
            from scraper.pipelines.postgres import PostgresBatchPipeline
            for pipeline in spider.crawler.engine.scraper.itemproc.middlewares:
                if isinstance(pipeline, PostgresBatchPipeline):
                    self._postgres_pipeline = pipeline
                    break
        return item

    def _dispatch(self, house_ids: list[int]):
        try:
            self._celery.send_task(
                "ai_insights.tasks.compute_insights",
                kwargs={"house_ids": house_ids},
                queue="insights",
            )
            logger.info(
                "Dispatched compute_insights task for %d houses", len(house_ids)
            )
        except Exception:
            logger.exception(
                "Failed to dispatch compute_insights task for house_ids=%s", house_ids
            )
