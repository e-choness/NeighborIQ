"""
Test configuration for house-api-service.

Uses a module-scoped TestClient so the lifespan (init_db) runs once before all tests.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    """Module-scoped client that starts the lifespan (runs init_db)."""
    with TestClient(app) as c:
        yield c
