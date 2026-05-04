"""
Test configuration for auth-service.

Uses a module-scoped TestClient so the lifespan (init_db + JWT key generation)
runs once before all tests in the session.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    """Module-scoped client that starts the lifespan (runs init_db and key generation)."""
    with TestClient(app) as c:
        yield c
