"""
Elasticsearch indexing layer for NeighborIQ.

Implements the house index from the Phase 2C spec:
  - Full-text on title
  - Keyword filters on city/region
  - Float range on price
  - geo_point on location (WGS-84 lat/lon)
  - Float ai_score for AI-ranked search

Uses the official elasticsearch-py async client (elasticsearch[async]).
"""

from typing import Any, Dict, List, Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

# ────────────────────────────────────────────────────────────────────────────
# Index definition
# ────────────────────────────────────────────────────────────────────────────

HOUSE_INDEX = "houses"

HOUSE_INDEX_MAPPING: Dict[str, Any] = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "title": {"type": "text", "analyzer": "standard"},
            "community": {"type": "keyword"},
            "city": {"type": "keyword"},
            "region": {"type": "keyword"},
            "price": {"type": "float"},
            "area": {"type": "float"},
            "rooms": {"type": "integer"},
            "location": {"type": "geo_point"},   # {"lat": ..., "lon": ...}
            "ai_score": {"type": "float"},
        }
    }
}


# ────────────────────────────────────────────────────────────────────────────
# Index management
# ────────────────────────────────────────────────────────────────────────────


async def create_index_if_missing(client: AsyncElasticsearch) -> bool:
    """
    Create the houses index with the canonical mapping if it does not exist.

    Returns True if the index was created, False if it already existed.
    """
    exists = await client.indices.exists(index=HOUSE_INDEX)
    if exists.body:
        return False
    # ES client v8: pass mapping/settings as keyword args, not body=
    await client.indices.create(
        index=HOUSE_INDEX,
        mappings=HOUSE_INDEX_MAPPING["mappings"],
    )
    return True


# ────────────────────────────────────────────────────────────────────────────
# Single-document operations
# ────────────────────────────────────────────────────────────────────────────


async def index_house(client: AsyncElasticsearch, house: Dict[str, Any]) -> None:
    """
    Index (or re-index) a single house document.

    The document ID is the house's integer primary key cast to string.
    Calling this on an already-indexed house updates it in place.
    """
    doc = _house_to_doc(house)
    await client.index(
        index=HOUSE_INDEX,
        id=str(house["id"]),
        document=doc,
    )


async def delete_house(client: AsyncElasticsearch, house_id: int) -> bool:
    """
    Remove a house from the index.

    Returns True if the document was deleted, False if it was not found.
    """
    try:
        await client.delete(index=HOUSE_INDEX, id=str(house_id))
        return True
    except NotFoundError:
        return False


# ────────────────────────────────────────────────────────────────────────────
# Bulk operations
# ────────────────────────────────────────────────────────────────────────────


async def bulk_index_houses(
    client: AsyncElasticsearch, houses: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Bulk index a list of house dicts.

    Uses elasticsearch-py's async_bulk helper for efficiency.
    Returns {"indexed": N, "errors": [...]} summary.
    """
    actions = [
        {
            "_index": HOUSE_INDEX,
            "_id": str(h["id"]),
            "_source": _house_to_doc(h),
        }
        for h in houses
    ]
    success, errors = await async_bulk(client, actions, raise_on_error=False)
    return {"indexed": success, "errors": errors}


# ────────────────────────────────────────────────────────────────────────────
# Search
# ────────────────────────────────────────────────────────────────────────────


async def search_houses(
    client: AsyncElasticsearch,
    q: Optional[str] = None,
    city: Optional[str] = None,
    region: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: Optional[float] = None,
    sort_by_ai_score: bool = False,
    size: int = 50,
) -> Dict[str, Any]:
    """
    Search houses using full-text + keyword filter + geo-distance queries.

    Args:
        q:             Free-text query (multi-match on title, city, region)
        city:          Exact city filter
        region:        Exact region filter
        price_min:     Minimum price (yuan)
        price_max:     Maximum price (yuan)
        lat/lon:       Center point for proximity search
        radius_km:     Search radius in km (requires lat + lon)
        sort_by_ai_score: Sort results by ai_score descending
        size:          Max number of results to return

    Returns:
        Raw Elasticsearch response body (dict).
    """
    must: List[Dict] = []
    filter_: List[Dict] = []

    if q:
        must.append(
            {"multi_match": {"query": q, "fields": ["title", "city", "region"]}}
        )

    if city:
        filter_.append({"term": {"city": city}})
    if region:
        filter_.append({"term": {"region": region}})

    if price_min is not None or price_max is not None:
        price_range: Dict[str, float] = {}
        if price_min is not None:
            price_range["gte"] = price_min
        if price_max is not None:
            price_range["lte"] = price_max
        filter_.append({"range": {"price": price_range}})

    if lat is not None and lon is not None and radius_km is not None:
        filter_.append(
            {
                "geo_distance": {
                    "distance": f"{radius_km}km",
                    "location": {"lat": lat, "lon": lon},
                }
            }
        )

    query: Dict[str, Any] = {
        "bool": {
            "must": must if must else [{"match_all": {}}],
            "filter": filter_,
        }
    }

    sort: Optional[List] = None
    if sort_by_ai_score:
        sort = [{"ai_score": {"order": "desc"}}, "_score"]

    response = await client.search(
        index=HOUSE_INDEX,
        query=query,
        size=size,
        sort=sort,
    )
    return response.body


# ────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ────────────────────────────────────────────────────────────────────────────


def _house_to_doc(house: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a house dict (from ORM or scraper) to an ES document.

    Handles None lat/lon gracefully — omits the location field so
    geo queries don't fail for houses without coordinates.
    """
    doc: Dict[str, Any] = {
        "id": str(house.get("id")),
        "title": house.get("title") or "",
        "community": house.get("community") or "",
        "city": house.get("city") or "",
        "region": house.get("region") or "",
        "price": float(house.get("price") or 0),
        "area": float(house.get("area") or 0),
        "rooms": int(house.get("rooms") or 0),
        "ai_score": float(house.get("ai_score") or 0.0),
    }

    lat = house.get("latitude")
    lon = house.get("longitude")
    if lat is not None and lon is not None:
        doc["location"] = {"lat": float(lat), "lon": float(lon)}

    return doc
