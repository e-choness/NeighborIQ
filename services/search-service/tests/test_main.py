"""
Search service unit tests — Phase 3C.

Uses mocked Elasticsearch and Redis so no external services needed.
Tests cover:
- Health endpoint
- GET /api/v1/search (full-text + filter)
- GET /api/v1/search/nearby (geo-distance)
- Cache hit path
- Validation errors
"""
import sys
sys.path.insert(0, '/app')

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import app.main as search_main
from app.main import app

# ── Helpers ───────────────────────────────────────────────────────────────────

FAKE_HOUSE = {
    "id": "1",
    "title": "Cozy 2BR near Xuanwu Lake",
    "city": "nanjing",
    "region": "xuanwu",
    "price": 1800000.0,
    "area": 78.5,
    "rooms": 2,
    "location": {"lat": 32.08, "lon": 118.80},
    "ai_score": 82.5,
}

FAKE_ES_RESPONSE = {
    "hits": {
        "total": {"value": 1, "relation": "eq"},
        "hits": [{"_source": FAKE_HOUSE}],
    }
}


def _make_mock_es(response=None):
    """Return an AsyncMock ES client whose search() returns response."""
    mock = AsyncMock()
    mock.search = AsyncMock(return_value=_wrap_es_response(response or FAKE_ES_RESPONSE))
    return mock


def _wrap_es_response(data: dict):
    """Wrap a dict so .body returns the dict (mimics elasticsearch-py v8 ApiResponse)."""
    mock_resp = AsyncMock()
    mock_resp.body = data
    # Make `await client.search(...)` return an object with .body
    # elasticsearch-py v8 search returns an ObjectApiResponse; .get() delegates to body
    mock_resp.__getitem__ = lambda self, k: data[k]
    mock_resp.get = lambda k, default=None: data.get(k, default)
    return mock_resp


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        # Inject mocks after lifespan runs
        search_main._redis_client = AsyncMock()
        search_main._redis_client.get = AsyncMock(return_value=None)
        search_main._redis_client.setex = AsyncMock(return_value=True)
        search_main._es_client = _make_mock_es()
        yield c


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "search-service"


def test_search_no_params_returns_200(client: TestClient):
    """GET /api/v1/search with no params returns 200 and result shape."""
    search_main._es_client = _make_mock_es()
    resp = client.get("/api/v1/search")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_search_returns_hits(client: TestClient):
    """Response items contain house data from Elasticsearch hits."""
    search_main._es_client = _make_mock_es()
    resp = client.get("/api/v1/search?city=nanjing")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["city"] == "nanjing"


def test_search_with_price_range(client: TestClient):
    """price_min and price_max params are accepted without error."""
    search_main._es_client = _make_mock_es()
    resp = client.get("/api/v1/search?price_min=1000000&price_max=3000000")
    assert resp.status_code == 200


def test_search_sort_by_ai_score(client: TestClient):
    """sort_by_ai_score=true is accepted without error."""
    search_main._es_client = _make_mock_es()
    resp = client.get("/api/v1/search?sort_by_ai_score=true")
    assert resp.status_code == 200


def test_search_size_validation(client: TestClient):
    """size > 200 should return 422."""
    resp = client.get("/api/v1/search?size=999")
    assert resp.status_code == 422


def test_search_nearby_returns_200(client: TestClient):
    """GET /api/v1/search/nearby with required lat/lon returns 200."""
    search_main._es_client = _make_mock_es()
    resp = client.get("/api/v1/search/nearby?lat=32.08&lon=118.80&radius_km=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data


def test_search_nearby_missing_lat_returns_422(client: TestClient):
    """Missing lat/lon must return 422."""
    resp = client.get("/api/v1/search/nearby?lon=118.80")
    assert resp.status_code == 422


def test_search_nearby_missing_lon_returns_422(client: TestClient):
    resp = client.get("/api/v1/search/nearby?lat=32.08")
    assert resp.status_code == 422


def test_search_cache_hit_skips_elasticsearch(client: TestClient):
    """When Redis returns a cached result, ES should not be called."""
    cached_payload = {"total": 5, "items": [FAKE_HOUSE]}
    search_main._redis_client.get = AsyncMock(
        return_value=json.dumps(cached_payload)
    )
    mock_es = _make_mock_es()
    search_main._es_client = mock_es

    resp = client.get("/api/v1/search?city=nanjing")
    assert resp.status_code == 200
    # ES search must NOT have been called (cache hit)
    mock_es.search.assert_not_called()

    # Restore cache miss for subsequent tests
    search_main._redis_client.get = AsyncMock(return_value=None)


def test_search_empty_result(client: TestClient):
    """Empty ES result set is returned cleanly."""
    empty_response = {"hits": {"total": {"value": 0, "relation": "eq"}, "hits": []}}
    search_main._es_client = _make_mock_es(empty_response)
    resp = client.get("/api/v1/search?city=nonexistent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []
