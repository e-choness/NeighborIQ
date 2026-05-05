"""
Search service test configuration.

Uses FastAPI TestClient with mocked Elasticsearch and Redis clients
so tests can run without external services.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

import app.main as search_main
from app.main import app


@pytest.fixture(scope="module")
def client():
    """
    Module-scoped TestClient with ES and Redis clients pre-wired to mocks.

    We patch _es_client and _redis_client at module level before TestClient
    starts the lifespan so the app uses mocks instead of real connections.
    """
    # Mock Elasticsearch: search_houses is called from shared.search.elasticsearch
    # We patch the module-level clients directly after lifespan starts.
    with TestClient(app) as c:
        # Override the module-level clients with mocks after lifespan
        search_main._es_client = AsyncMock()
        search_main._redis_client = AsyncMock()
        # Redis cache miss by default
        search_main._redis_client.get = AsyncMock(return_value=None)
        search_main._redis_client.setex = AsyncMock(return_value=True)
        yield c
