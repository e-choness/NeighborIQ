"""
Persist canonical listings to PostgreSQL.

Upserts by `url` (the stable listing key) and appends a house_price_history row
whenever a listing is first seen or its price changes — this is what powers
price-drop signals and days-on-market. Used by the CLI loaders and by the
Scrapy PostgresBatchPipeline.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_UPSERT = text("""
    INSERT INTO house_houses
        (title, community, city, region, street, postal_code, property_type,
         price, sqft, area, rooms, bathrooms, parking, floor, decoration, age,
         condo_fee, property_tax, status, listed_at,
         latitude, longitude, url, images, source, is_synthetic,
         is_active, created_at, updated_at)
    VALUES
        (:title, :community, :city, :region, :street, :postal_code, :property_type,
         :price, :sqft, :area, :rooms, :bathrooms, :parking, :floor, :decoration, :age,
         :condo_fee, :property_tax, :status, :listed_at,
         :latitude, :longitude, :url, :images, :source, :is_synthetic,
         :is_active, :now, :now)
    ON CONFLICT (url) DO UPDATE SET
        title         = EXCLUDED.title,
        community     = EXCLUDED.community,
        street        = EXCLUDED.street,
        postal_code   = EXCLUDED.postal_code,
        property_type = EXCLUDED.property_type,
        price         = EXCLUDED.price,
        sqft          = EXCLUDED.sqft,
        area          = EXCLUDED.area,
        rooms         = EXCLUDED.rooms,
        bathrooms     = EXCLUDED.bathrooms,
        parking       = EXCLUDED.parking,
        floor         = EXCLUDED.floor,
        decoration    = EXCLUDED.decoration,
        age           = EXCLUDED.age,
        condo_fee     = EXCLUDED.condo_fee,
        property_tax  = EXCLUDED.property_tax,
        status        = EXCLUDED.status,
        listed_at     = COALESCE(house_houses.listed_at, EXCLUDED.listed_at),
        latitude      = EXCLUDED.latitude,
        longitude     = EXCLUDED.longitude,
        images        = EXCLUDED.images,
        is_active     = EXCLUDED.is_active,
        updated_at    = EXCLUDED.updated_at
    RETURNING id
""")

_HISTORY = text("""
    INSERT INTO house_price_history (house_id, price, recorded_at)
    VALUES (:house_id, :price, :recorded_at)
""")


def _params(item: dict, now: datetime) -> dict:
    return {
        "title": item.get("title") or "",
        "community": item.get("community") or "",
        "city": item.get("city") or "",
        "region": item.get("region") or "",
        "street": item.get("street"),
        "postal_code": item.get("postal_code"),
        "property_type": item.get("property_type"),
        "price": int(item["price"]),
        "sqft": item.get("sqft"),
        "area": item.get("area"),
        "rooms": item.get("rooms"),
        "bathrooms": item.get("bathrooms"),
        "parking": item.get("parking"),
        "floor": item.get("floor"),
        "decoration": item.get("decoration"),
        "age": item.get("age"),
        "condo_fee": item.get("condo_fee"),
        "property_tax": item.get("property_tax"),
        "status": item.get("status") or "active",
        "listed_at": item.get("listed_at"),
        "latitude": item.get("latitude"),
        "longitude": item.get("longitude"),
        "url": item["url"],
        "images": json.dumps(item.get("images") or []),
        "source": item.get("source") or "import",
        "is_synthetic": 1 if item.get("is_synthetic") else 0,
        "is_active": 1 if (item.get("status") or "active") == "active" else 0,
        "now": now,
    }


def upsert_listings(session: Session, items: list[dict], now: datetime | None = None) -> list[int]:
    """
    Insert or update normalized, validated listings. Returns their house ids.

    Price history: on first insert, any supplied `price_history` rows are loaded
    (seed data carries earlier asking prices); then the current price is
    recorded if it differs from the most recent history row.
    Caller owns the transaction (commit/rollback).
    """
    if not items:
        return []
    now = now or datetime.now(UTC)

    urls = [i["url"] for i in items]
    existing = {
        row.url: row.id
        for row in session.execute(
            text("SELECT id, url FROM house_houses WHERE url = ANY(:urls)"), {"urls": urls}
        )
    }

    ids: list[int] = []
    for item in items:
        house_id = session.execute(_UPSERT, _params(item, now)).scalar_one()
        ids.append(house_id)

        if item["url"] not in existing:
            for point in item.get("price_history") or []:
                if point.get("price") and point.get("recorded_at"):
                    session.execute(_HISTORY, {"house_id": house_id, **point})

        last = session.execute(
            text("""
                SELECT price FROM house_price_history
                WHERE house_id = :id ORDER BY recorded_at DESC, id DESC LIMIT 1
            """),
            {"id": house_id},
        ).scalar()
        if last != int(item["price"]):
            # A brand-new listing's first price dates from when it was listed
            first_seen = last is None and item.get("listed_at")
            session.execute(
                _HISTORY,
                {
                    "house_id": house_id,
                    "price": int(item["price"]),
                    "recorded_at": item["listed_at"] if first_seen else now,
                },
            )

    return ids


def refresh_communities(session: Session) -> int:
    """
    Sync house_communities aggregates with active listings, keeping row ids stable
    (clients link to /communities/{id}). Returns the number of communities.
    """
    stats = """
        SELECT community AS name, city, MIN(region) AS region,
               AVG(latitude) AS latitude, AVG(longitude) AS longitude,
               COUNT(*) AS house_count, AVG(price) AS avg_price,
               MIN(price) AS min_price, MAX(price) AS max_price
        FROM house_houses
        WHERE is_active = 1 AND community <> ''
        GROUP BY community, city
    """
    session.execute(
        text(f"""
        UPDATE house_communities c SET
            region = s.region, latitude = s.latitude, longitude = s.longitude,
            house_count = s.house_count, avg_price = s.avg_price,
            min_price = s.min_price, max_price = s.max_price, updated_at = NOW()
        FROM ({stats}) s
        WHERE c.name = s.name AND c.city = s.city
    """)
    )
    session.execute(
        text(f"""
        INSERT INTO house_communities
            (name, city, region, latitude, longitude, house_count,
             avg_price, min_price, max_price, created_at, updated_at)
        SELECT s.name, s.city, s.region, s.latitude, s.longitude, s.house_count,
               s.avg_price, s.min_price, s.max_price, NOW(), NOW()
        FROM ({stats}) s
        WHERE NOT EXISTS (
            SELECT 1 FROM house_communities c WHERE c.name = s.name AND c.city = s.city
        )
    """)
    )
    # Neighbourhoods with no active listings stay (ids remain valid) but read as empty
    session.execute(
        text(f"""
        UPDATE house_communities c SET house_count = 0, updated_at = NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM ({stats}) s WHERE c.name = s.name AND c.city = s.city
        )
    """)
    )
    return session.execute(text("SELECT COUNT(*) FROM house_communities WHERE house_count > 0")).scalar() or 0
