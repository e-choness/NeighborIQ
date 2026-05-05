"""
Test configuration for auth-service.

Uses a module-scoped TestClient so the lifespan (init_db + JWT key generation)
runs once before all tests in the session.
"""
import asyncio
import os

import asyncpg
import pytest
from fastapi.testclient import TestClient

from app.main import app

# Emails created by logout/signup tests — cleaned up before each run
_TEST_EMAILS = ["logout_test@example.com", "logout_cookies_test@example.com"]


@pytest.fixture(scope="module", autouse=True)
def cleanup_test_users():
    """
    Delete test-specific users (and their refresh tokens) before any tests run.

    Prevents 409 Conflict when the PostgreSQL volume retains data from a prior run.
    """
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://root:root@postgres:5432/house_discovery",
    ).replace("postgresql+asyncpg://", "postgresql://")

    async def _cleanup():
        try:
            conn = await asyncpg.connect(db_url)
            try:
                await conn.execute(
                    "DELETE FROM auth_refresh_tokens WHERE user_id IN "
                    "(SELECT id FROM auth_users WHERE email = ANY($1::text[]))",
                    _TEST_EMAILS,
                )
                await conn.execute(
                    "DELETE FROM auth_users WHERE email = ANY($1::text[])",
                    _TEST_EMAILS,
                )
            finally:
                await conn.close()
        except Exception:
            pass  # DB may not exist yet on first run — ignore

    asyncio.run(_cleanup())
    yield


@pytest.fixture(scope="module")
def client(cleanup_test_users):
    """Module-scoped client that starts the lifespan (runs init_db and key generation)."""
    with TestClient(app) as c:
        yield c
