"""
PostgreSQL batch-insert pipeline.

Accumulates items in a buffer and flushes to PostgreSQL when
the batch size is reached or when the spider closes.

Uses synchronous SQLAlchemy + psycopg2 (Scrapy is synchronous). Row-level
logic (upsert by url + price history) lives in ingestion/writer.py so the CLI
loaders and this pipeline write identically.
"""
import logging
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from ingestion.writer import refresh_communities, upsert_listings

logger = logging.getLogger(__name__)


class PostgresBatchPipeline:
    """
    Buffers validated listing items and upserts them in batches.
    """

    def __init__(self, database_url: str, batch_size: int):
        self.database_url = database_url
        self.batch_size = batch_size
        self._buffer: list[dict[str, Any]] = []
        self._engine = None
        self._SessionLocal = None
        self.inserted_ids: list[int] = []  # Collected for Celery dispatch pipeline

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            database_url=crawler.settings.get(
                "DATABASE_URL", "postgresql://root:root@localhost:5432/house_discovery"
            ),
            batch_size=crawler.settings.getint("POSTGRES_BATCH_SIZE", 50),
        )

    def open_spider(self, spider):
        self._engine = create_engine(self.database_url, pool_pre_ping=True)
        self._SessionLocal = sessionmaker(bind=self._engine)

    def close_spider(self, spider):
        if self._buffer:
            self._flush()
        if self._engine:
            self._engine.dispose()

    def process_item(self, item, spider):
        self._buffer.append(dict(item))
        if len(self._buffer) >= self.batch_size:
            self._flush()
        return item

    def _flush(self):
        if not self._buffer:
            return

        session: Session = self._SessionLocal()
        try:
            inserted = upsert_listings(session, self._buffer)
            refresh_communities(session)
            self.inserted_ids.extend(inserted)
            session.commit()
            logger.info("Flushed %d listings to PostgreSQL", len(self._buffer))
        except Exception:
            session.rollback()
            logger.exception("Failed to flush batch to PostgreSQL")
        finally:
            session.close()
            self._buffer.clear()
