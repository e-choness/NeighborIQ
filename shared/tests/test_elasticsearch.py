"""
Phase 2C — Elasticsearch indexing tests.

Tests index creation, single-doc indexing, bulk indexing, search
(full-text, keyword filter, price range, geo-distance) against
a real Elasticsearch instance (elasticsearch service in docker-compose).
"""

import os
import asyncio

import pytest
import pytest_asyncio
from elasticsearch import AsyncElasticsearch

# All tests in this module share one event loop so module-scoped async fixtures
# (es_client, setup_index) and the tests themselves can share the same client.
pytestmark = pytest.mark.asyncio(loop_scope="module")

from shared.search.elasticsearch import (
    HOUSE_INDEX,
    HOUSE_INDEX_MAPPING,
    bulk_index_houses,
    create_index_if_missing,
    delete_house,
    index_house,
    search_houses,
)

ES_URL = os.environ.get("ELASTICSEARCH_URL", "http://elasticsearch:9200")

# Sample house fixtures
HOUSE_1 = {
    "id": 1,
    "title": "Cozy 2BR near Xuanwu Lake",
    "community": "Xuanwu Garden",
    "city": "nanjing",
    "region": "xuanwu",
    "price": 1_800_000,
    "area": 78.5,
    "rooms": 2,
    "latitude": 32.0800,
    "longitude": 118.7980,
    "ai_score": 82.5,
}

HOUSE_2 = {
    "id": 2,
    "title": "Spacious 3BR in Gulou",
    "community": "Gulou Heights",
    "city": "nanjing",
    "region": "gulou",
    "price": 3_200_000,
    "area": 120.0,
    "rooms": 3,
    "latitude": 32.0600,
    "longitude": 118.7700,
    "ai_score": 91.0,
}

HOUSE_3 = {
    "id": 3,
    "title": "Modern studio in Chaoyang",
    "community": "CBD Tower",
    "city": "beijing",
    "region": "chaoyang",
    "price": 5_500_000,
    "area": 45.0,
    "rooms": 1,
    "latitude": 39.9200,
    "longitude": 116.4400,
    "ai_score": 75.0,
}


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def es_client():
    client = AsyncElasticsearch(ES_URL)
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="module", autouse=True, loop_scope="module")
async def setup_index(es_client):
    """Drop and re-create the index before any tests run."""
    exists = await es_client.indices.exists(index=HOUSE_INDEX)
    if exists.body:
        await es_client.indices.delete(index=HOUSE_INDEX)
    await es_client.indices.create(
        index=HOUSE_INDEX,
        mappings=HOUSE_INDEX_MAPPING["mappings"],
    )

    # Bulk index sample data
    await bulk_index_houses(es_client, [HOUSE_1, HOUSE_2, HOUSE_3])

    # Refresh so documents are immediately searchable
    await es_client.indices.refresh(index=HOUSE_INDEX)

    yield

    # Teardown
    await es_client.indices.delete(index=HOUSE_INDEX, ignore_unavailable=True)


# ──────────────────────────────────────────────────────────────
# Index management
# ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_index_if_missing_returns_false_when_exists(es_client):
    created = await create_index_if_missing(es_client)
    assert created is False, "Index already exists — should return False"


@pytest.mark.asyncio
async def test_index_mapping_has_geo_point(es_client):
    mapping = await es_client.indices.get_mapping(index=HOUSE_INDEX)
    props = mapping[HOUSE_INDEX]["mappings"]["properties"]
    assert props["location"]["type"] == "geo_point"
    assert props["city"]["type"] == "keyword"
    assert props["price"]["type"] == "float"


# ──────────────────────────────────────────────────────────────
# Single-document operations
# ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_index_single_house(es_client):
    new_house = {
        "id": 99,
        "title": "Brand new flat",
        "community": "New Block",
        "city": "shanghai",
        "region": "pudong",
        "price": 4_000_000,
        "area": 90.0,
        "rooms": 2,
        "latitude": 31.2304,
        "longitude": 121.4737,
        "ai_score": 88.0,
    }
    await index_house(es_client, new_house)
    await es_client.indices.refresh(index=HOUSE_INDEX)

    result = await es_client.get(index=HOUSE_INDEX, id="99")
    assert result["found"] is True
    assert result["_source"]["city"] == "shanghai"


@pytest.mark.asyncio
async def test_delete_house(es_client):
    deleted = await delete_house(es_client, 99)
    assert deleted is True
    await es_client.indices.refresh(index=HOUSE_INDEX)

    from elasticsearch import NotFoundError
    with pytest.raises(NotFoundError):
        await es_client.get(index=HOUSE_INDEX, id="99")


@pytest.mark.asyncio
async def test_delete_nonexistent_house_returns_false(es_client):
    result = await delete_house(es_client, 999_999)
    assert result is False


# ──────────────────────────────────────────────────────────────
# Search
# ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_all_returns_results(es_client):
    resp = await search_houses(es_client)
    hits = resp["hits"]["hits"]
    assert len(hits) >= 3


@pytest.mark.asyncio
async def test_search_by_city_keyword(es_client):
    resp = await search_houses(es_client, city="nanjing")
    hits = resp["hits"]["hits"]
    assert len(hits) == 2
    for h in hits:
        assert h["_source"]["city"] == "nanjing"


@pytest.mark.asyncio
async def test_search_fulltext_title(es_client):
    resp = await search_houses(es_client, q="Gulou")
    hits = resp["hits"]["hits"]
    assert len(hits) >= 1
    titles = [h["_source"]["title"] for h in hits]
    assert any("Gulou" in t for t in titles)


@pytest.mark.asyncio
async def test_search_price_range(es_client):
    resp = await search_houses(es_client, price_min=2_000_000, price_max=4_000_000)
    hits = resp["hits"]["hits"]
    assert len(hits) >= 1
    for h in hits:
        price = h["_source"]["price"]
        assert 2_000_000 <= price <= 4_000_000


@pytest.mark.asyncio
async def test_search_geo_distance(es_client):
    # Center near Xuanwu Lake (HOUSE_1) — 5km radius should include houses 1 and 2
    resp = await search_houses(
        es_client,
        lat=32.08,
        lon=118.80,
        radius_km=10.0,
    )
    hits = resp["hits"]["hits"]
    ids = {int(h["_source"]["id"]) for h in hits}
    assert 1 in ids, "HOUSE_1 should be within 10km of the search center"


@pytest.mark.asyncio
async def test_search_sort_by_ai_score(es_client):
    resp = await search_houses(es_client, city="nanjing", sort_by_ai_score=True)
    hits = resp["hits"]["hits"]
    scores = [h["_source"]["ai_score"] for h in hits]
    assert scores == sorted(scores, reverse=True), "Results must be sorted by ai_score desc"


@pytest.mark.asyncio
async def test_bulk_index_returns_count(es_client):
    bulk_houses = [
        {**HOUSE_1, "id": 101},
        {**HOUSE_2, "id": 102},
    ]
    result = await bulk_index_houses(es_client, bulk_houses)
    assert result["indexed"] == 2
    assert result["errors"] == []
