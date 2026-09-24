"""
Shared fixtures for the API tests. Requires PostgreSQL (the Docker test profile
provides one); tables are created with create_all for speed.
"""
import os
import uuid

os.environ.setdefault("SECURE_COOKIES", "0")  # TestClient speaks plain http
os.environ.setdefault("ADMIN_EMAILS", "admin_bootstrap_test@example.com")
os.environ.setdefault("AUTH_RATE_LIMIT", "1000/minute")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://root:root@postgres:5432/house_discovery")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _signup(client: TestClient, email: str) -> dict:
    """Sign up in a fresh cookie jar and return that user's auth header."""
    with TestClient(app) as c:
        r = c.post("/api/v1/auth/signup", json={"email": email, "password": "secure_password123"})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {c.cookies['access_token']}"}


@pytest.fixture(scope="session")
def user_headers(client):
    return _signup(client, f"user_{uuid.uuid4().hex[:8]}@example.com")


@pytest.fixture(scope="session")
def admin_headers(client):
    """ADMIN_EMAILS bootstraps admins; reuse the account if an earlier run created it."""
    from app.routers import auth

    email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    auth.ADMIN_EMAILS.add(email)
    return _signup(client, email)
