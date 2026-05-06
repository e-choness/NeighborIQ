"""
Test configuration for portfolio-service.

Patches init_db/dispose_db to no-ops for unit tests that don't need
a real database connection (auth boundary tests).
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Module-scoped client with init_db patched out for unit tests."""
    with (
        patch("app.main.init_db", new_callable=AsyncMock),
        patch("app.main.dispose_db", new_callable=AsyncMock),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c
