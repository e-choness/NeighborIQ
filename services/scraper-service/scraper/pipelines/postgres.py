"""
PostgreSQL batch-insert pipeline.

Accumulates items in a buffer and flushes to PostgreSQL when
the batch size is reached or when the spider closes.

Uses synchronous SQLAlchemy + psycopg2 (Scrapy is synchronous).
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)


class PostgresBatchPipeline:
    """
    Buffers validated house items and inserts them in batches.
    Uses ON CONFLICT (url) DO UPDATE to handle re-crawl of existing houses.
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
            inserted = self._upsert_batch(session, self._buffer)
            self.inserted_ids.extend(inserted)
            session.commit()
            logger.info("Flushed %d houses to PostgreSQL", len(self._buffer))
        except Exception:
            session.rollback()
            logger.exception("Failed to flush batch to PostgreSQL")
        finally:
            session.close()
            self._buffer.clear()

    def _upsert_batch(self, session: Session, items: list[dict]) -> list[int]:
        """
        Insert or update houses by URL (unique constraint).
        Returns list of inserted/updated row IDs.
        """
        now = datetime.now(timezone.utc)
        ids: list[int] = []

        for item in items:
            images_json = json.dumps(item.get("images") or [])
            result = session.execute(
                text("""
                    INSERT INTO house_houses
                        (title, community, city, region, street,
                         price, area, rooms, floor, decoration, age,
                         latitude, longitude, url, images,
                         is_active, created_at, updated_at)
                    VALUES
                        (:title, :community, :city, :region, :street,
                         :price, :area, :rooms, :floor, :decoration, :age,
                         :latitude, :longitude, :url, :images,
                         1, :now, :now)
                    ON CONFLICT (url) DO UPDATE SET
                        title       = EXCLUDED.title,
                        price       = EXCLUDED.price,
                        area        = EXCLUDED.area,
                        rooms       = EXCLUDED.rooms,
                        floor       = EXCLUDED.floor,
                        decoration  = EXCLUDED.decoration,
                        age         = EXCLUDED.age,
                        latitude    = EXCLUDED.latitude,
                        longitude   = EXCLUDED.longitude,
                        images      = EXCLUDED.images,
                        updated_at  = EXCLUDED.updated_at
                    RETURNING id
                """),
                {
                    "title":      item.get("title") or "",
                    "community":  item.get("community") or "",
                    "city":       item.get("city") or "",
                    "region":     item.get("region") or "",
                    "street":     item.get("street") or "",
                    "price":      int(item.get("price") or 0),
                    "area":       float(item.get("area") or 0),
                    "rooms":      item.get("rooms"),
                    "floor":      item.get("floor"),
                    "decoration": item.get("decoration"),
                    "age":        item.get("age"),
                    "latitude":   item.get("latitude"),
                    "longitude":  item.get("longitude"),
                    "url":        item.get("url"),
                    "images":     images_json,
                    "now":        now,
                },
            )
            row = result.fetchone()
            if row:
                ids.append(row[0])

        return ids
