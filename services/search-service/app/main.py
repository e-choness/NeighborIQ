"""
Search Service — full-text + geo-spatial house search via Elasticsearch.

Phase 3C responsibilities:
  - GET /api/v1/search          Full-text + filter search
  - GET /api/v1/search/nearby   Geo-distance proximity search
  - Results cached in Redis (30-min TTL keyed on query hash)
"""

import os
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI, Query

from shared.search.elasticsearch import search_houses, HOUSE_INDEX
from shared.cache.redis_cache import SEARCH_TTL, hash_query, get_cached, set_cached
from shared.models.schemas import HealthResponse

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://elasticsearch:9200")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

_es_client: Optional[AsyncElasticsearch] = None
_redis_client: Optional[aioredis.Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _es_client, _redis_client
    logger.info("Starting Search Service...")
    _es_client = AsyncElasticsearch(ELASTICSEARCH_URL)
    _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    logger.info("Search Service started.")
    yield
    logger.info("Shutting down Search Service...")
    await _es_client.close()
    await _redis_client.aclose()


app = FastAPI(
    title="NeighborIQ Search Service",
    version="0.1.0",
    description="Elasticsearch-backed full-text + geo-spatial house search with Redis caching.",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Service health checks"},
        {"name": "search", "description": "House search endpoints"},
    ],
)


# ============================================================================
# Health
# ============================================================================


@app.get("/health", tags=["health"], response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        service="search-service",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
    )


# ============================================================================
# Search
# ============================================================================


@app.get("/api/v1/search", tags=["search"])
async def search(
    q: Optional[str] = Query(default=None, description="Full-text query"),
    city: Optional[str] = Query(default=None, description="Filter by city (keyword)"),
    region: Optional[str] = Query(default=None, description="Filter by region (keyword)"),
    price_min: Optional[float] = Query(default=None, description="Minimum price (yuan)"),
    price_max: Optional[float] = Query(default=None, description="Maximum price (yuan)"),
    sort_by_ai_score: bool = Query(default=False, description="Sort by ai_score descending"),
    size: int = Query(default=50, ge=1, le=200, description="Max results"),
):
    """
    Full-text + keyword filter house search backed by Elasticsearch.

    Results are cached in Redis for 30 minutes keyed on the query parameters.
    """
    params = {
        "q": q,
        "city": city,
        "region": region,
        "price_min": price_min,
        "price_max": price_max,
        "sort_by_ai_score": sort_by_ai_score,
        "size": size,
    }
    cache_key = f"search:query:{hash_query(params)}"

    # Cache read
    if _redis_client:
        cached = await get_cached(_redis_client, cache_key)
        if cached is not None:
            return cached

    # Elasticsearch query
    raw = await search_houses(
        _es_client,
        q=q,
        city=city,
        region=region,
        price_min=price_min,
        price_max=price_max,
        sort_by_ai_score=sort_by_ai_score,
        size=size,
    )

    hits = raw.get("hits", {}).get("hits", [])
    result = {
        "total": raw.get("hits", {}).get("total", {}).get("value", 0),
        "items": [h["_source"] for h in hits],
    }

    # Cache write
    if _redis_client:
        await set_cached(_redis_client, cache_key, result, SEARCH_TTL)

    return result


@app.get("/api/v1/search/nearby", tags=["search"])
async def search_nearby(
    lat: float = Query(..., description="Center latitude (WGS-84)"),
    lon: float = Query(..., description="Center longitude (WGS-84)"),
    radius_km: float = Query(default=5.0, gt=0, description="Search radius in km"),
    city: Optional[str] = Query(default=None, description="Filter by city"),
    price_min: Optional[float] = Query(default=None, description="Minimum price"),
    price_max: Optional[float] = Query(default=None, description="Maximum price"),
    size: int = Query(default=50, ge=1, le=200, description="Max results"),
):
    """
    Geo-distance proximity search: find houses within radius_km of (lat, lon).
    """
    params = {
        "lat": lat,
        "lon": lon,
        "radius_km": radius_km,
        "city": city,
        "price_min": price_min,
        "price_max": price_max,
        "size": size,
    }
    cache_key = f"search:query:{hash_query(params)}"

    # Cache read
    if _redis_client:
        cached = await get_cached(_redis_client, cache_key)
        if cached is not None:
            return cached

    raw = await search_houses(
        _es_client,
        city=city,
        price_min=price_min,
        price_max=price_max,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        size=size,
    )

    hits = raw.get("hits", {}).get("hits", [])
    result = {
        "total": raw.get("hits", {}).get("total", {}).get("value", 0),
        "items": [h["_source"] for h in hits],
    }

    if _redis_client:
        await set_cached(_redis_client, cache_key, result, SEARCH_TTL)

    return result
