"""
Phase 2B — Redis cache layer tests.

Tests key builders, TTL constants, set/get/invalidate, get_or_set
against a real Redis instance (redis service in docker-compose).
"""

import os

import pytest
import pytest_asyncio
import redis.asyncio as aioredis

from shared.cache.redis_cache import (
    COMMUNITY_TTL,
    HOUSE_TTL,
    SEARCH_TTL,
    community_key,
    get_cached,
    get_or_set,
    hash_query,
    house_key,
    invalidate,
    search_key,
    set_cached,
)

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")


@pytest_asyncio.fixture
async def redis_client():
    client = aioredis.from_url(REDIS_URL, decode_responses=True)
    yield client
    await client.aclose()


# ──────────────────────────────────────────────────────────────
# Key builder tests (pure, no Redis needed)
# ──────────────────────────────────────────────────────────────


def test_house_key_format():
    assert house_key(42) == "house:42"


def test_community_key_format():
    key = community_key("nanjing", "gulou", "zhongshan-road")
    assert key == "community:nanjing:gulou:zhongshan-road"


def test_search_key_format():
    assert search_key("abc123").startswith("search:query:")


def test_hash_query_stable():
    q1 = hash_query({"city": "nanjing", "price_min": 1000000})
    q2 = hash_query({"price_min": 1000000, "city": "nanjing"})
    assert q1 == q2, "hash_query must be order-independent"


def test_hash_query_length():
    h = hash_query({"city": "beijing"})
    assert len(h) == 16


# ──────────────────────────────────────────────────────────────
# TTL constants
# ──────────────────────────────────────────────────────────────


def test_ttl_values():
    assert HOUSE_TTL == 86_400
    assert COMMUNITY_TTL == 604_800
    assert SEARCH_TTL == 1_800


# ──────────────────────────────────────────────────────────────
# Redis integration tests
# ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_and_get_cached(redis_client):
    key = house_key(9001)
    value = {"id": 9001, "title": "Test House", "price": 2_000_000}

    await set_cached(redis_client, key, value, HOUSE_TTL)
    result = await get_cached(redis_client, key)

    assert result == value


@pytest.mark.asyncio
async def test_get_cached_missing_key_returns_none(redis_client):
    result = await get_cached(redis_client, "house:nonexistent_key_xyz")
    assert result is None


@pytest.mark.asyncio
async def test_invalidate_removes_key(redis_client):
    key = house_key(9002)
    await set_cached(redis_client, key, {"id": 9002}, HOUSE_TTL)

    await invalidate(redis_client, key)
    result = await get_cached(redis_client, key)

    assert result is None


@pytest.mark.asyncio
async def test_invalidate_nonexistent_key_is_safe(redis_client):
    # Must not raise
    await invalidate(redis_client, "house:does_not_exist_xyz")


@pytest.mark.asyncio
async def test_get_or_set_populates_cache(redis_client):
    key = search_key(hash_query({"city": "nanjing"}))
    # Clean state
    await invalidate(redis_client, key)

    call_count = {"n": 0}

    async def fetch():
        call_count["n"] += 1
        return [{"id": 1, "title": "House A"}]

    result1 = await get_or_set(redis_client, key, fetch, SEARCH_TTL)
    result2 = await get_or_set(redis_client, key, fetch, SEARCH_TTL)

    assert result1 == [{"id": 1, "title": "House A"}]
    assert result2 == result1
    assert call_count["n"] == 1, "fetch_fn should only be called once"


@pytest.mark.asyncio
async def test_get_or_set_none_not_cached(redis_client):
    key = house_key(9999)
    await invalidate(redis_client, key)

    async def fetch_none():
        return None

    result = await get_or_set(redis_client, key, fetch_none, HOUSE_TTL)
    assert result is None
    # Key should not be set in Redis
    raw = await redis_client.get(key)
    assert raw is None


@pytest.mark.asyncio
async def test_community_key_caching(redis_client):
    key = community_key("beijing", "chaoyang", "sanlitun")
    data = {"name": "Sanlitun Community", "house_count": 120}

    await set_cached(redis_client, key, data, COMMUNITY_TTL)
    result = await get_cached(redis_client, key)

    assert result == data
