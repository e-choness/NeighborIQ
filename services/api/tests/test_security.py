"""Authorization boundaries — the rules the old gateway used to enforce."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_spoofed_identity_headers_are_ignored() -> None:
    """X-User-ID was trusted by the old services; it must mean nothing now."""
    with TestClient(app) as c:
        r = c.get("/api/v1/portfolio/saved", headers={"X-User-ID": "1", "X-User-Role": "admin"})
        assert r.status_code == 401
        r = c.post("/api/v1/houses", json={}, headers={"X-User-ID": "1", "X-User-Role": "admin"})
        assert r.status_code == 401


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/v1/houses"),
        ("PUT", "/api/v1/houses/1"),
        ("DELETE", "/api/v1/houses/1"),
        ("POST", "/api/v1/admin/ingest"),
        ("GET", "/api/v1/admin/status"),
        ("POST", "/api/v1/admin/insights/retrain"),
    ],
)
def test_admin_routes(method, path, user_headers) -> None:
    with TestClient(app) as c:
        assert c.request(method, path).status_code == 401
        assert c.request(method, path, headers=user_headers).status_code == 403


def test_garbage_token_on_protected_route() -> None:
    with TestClient(app) as c:
        r = c.get("/api/v1/portfolio/saved", headers={"Authorization": "Bearer garbage"})
        assert r.status_code == 401


def test_garbage_token_ignored_on_public_route() -> None:
    with TestClient(app) as c:
        assert c.get("/api/v1/houses", headers={"Authorization": "Bearer garbage"}).status_code == 200


def test_credential_endpoints_have_their_own_rate_limit() -> None:
    """Brute-force protection: signup/login carry a route-specific limit."""
    from app.limits import limiter

    limited = set(limiter._route_limits)
    assert {"app.routers.auth.login", "app.routers.auth.signup"} <= limited
