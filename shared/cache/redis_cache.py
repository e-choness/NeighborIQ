"""
Redis cache layer for NeighborIQ.

Implements the cache-aside pattern with the three key namespaces from the plan:
  house:{id}                   — 24h TTL
  community:{city}:{region}:{street} — 7d TTL
  search:query:{hash}          — 30m TTL

All values are JSON-serialized. redis.asyncio (part of redis-py ≥ 4.2) is used.
"""

import hashlib
import json
from typing import Any, Callable, Optional

import redis.asyncio as aioredis

# ────────────────────────────────────────────────────────────────────────────
# TTL constants (seconds)
# ────────────────────────────────────────────────────────────────────────────

HOUSE_TTL: int = 86_400       # 24 hours
COMMUNITY_TTL: int = 604_800  # 7 days
SEARCH_TTL: int = 1_800       # 30 minutes


# ────────────────────────────────────────────────────────────────────────────
# Key builders
# ────────────────────────────────────────────────────────────────────────────


def house_key(house_id: int) -> str:
    """Cache key for a single house document."""
    return f"house:{house_id}"


def community_key(city: str, region: str, street: str) -> str:
    """Cache key for a community (city + region + street triple)."""
    return f"community:{city}:{region}:{street}"


def search_key(query_hash: str) -> str:
    """Cache key for a search result set (identified by query hash)."""
    return f"search:query:{query_hash}"


def hash_query(query_dict: dict) -> str:
    """
    Create a stable 16-char hex hash from a search query dict.

    Keys are sorted before serialization so that query parameter order
    does not produce different hashes for the same logical query.
    """
    serialized = json.dumps(query_dict, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


# ────────────────────────────────────────────────────────────────────────────
# Cache operations
# ────────────────────────────────────────────────────────────────────────────


async def get_cached(client: aioredis.Redis, key: str) -> Optional[Any]:
    """
    Retrieve a cached value.

    Returns the deserialized value, or None if the key is missing or expired.
    """
    raw = await client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def set_cached(client: aioredis.Redis, key: str, value: Any, ttl: int) -> None:
    """
    Store a value in the cache with an expiry.

    Args:
        client: Async Redis client
        key:    Cache key
        value:  JSON-serializable value
        ttl:    Time-to-live in seconds
    """
    await client.setex(key, ttl, json.dumps(value, default=str))


async def invalidate(client: aioredis.Redis, key: str) -> None:
    """
    Delete a cached key (cache invalidation).

    Called on scraper insert and after AI compute to force fresh reads.
    No-op if the key does not exist.
    """
    await client.delete(key)


async def get_or_set(
    client: aioredis.Redis,
    key: str,
    fetch_fn: Callable,
    ttl: int,
) -> Any:
    """
    Cache-aside: return cached value or populate from fetch_fn.

    Args:
        client:   Async Redis client
        key:      Cache key
        fetch_fn: Async callable that returns a JSON-serializable value
        ttl:      TTL to use when populating the cache

    Returns:
        Cached or freshly fetched value (None if fetch_fn returns None).
    """
    cached = await get_cached(client, key)
    if cached is not None:
        return cached

    value = await fetch_fn()
    if value is not None:
        await set_cached(client, key, value, ttl)
    return value
