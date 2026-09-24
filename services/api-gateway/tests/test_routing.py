"""Routing, authorization and header-hygiene tests for the gateway proxy.

Upstream services are replaced by an httpx.MockTransport that echoes what it
received, and JWKS is served from a locally generated key pair.
"""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

import app.main as gw
from shared.utils.jwt_utils import (
    create_access_token,
    generate_rsa_keypair,
    get_jwks_from_public_key,
    get_key_id,
)

PRIVATE_PEM, PUBLIC_PEM = generate_rsa_keypair()
KID = get_key_id(PUBLIC_PEM)


def _token(role: str) -> str:
    return create_access_token("42", private_key_pem=PRIVATE_PEM, key_id=KID, role=role)


def _echo(request: httpx.Request) -> httpx.Response:
    body = {
        "host": request.url.host,
        "path": request.url.path,
        "x_user_id": request.headers.get("x-user-id"),
        "x_user_role": request.headers.get("x-user-role"),
    }
    headers = [("content-type", "application/json")]
    if request.url.path.endswith("/login"):
        headers += [("set-cookie", "access_token=a; HttpOnly"), ("set-cookie", "refresh_token=r; HttpOnly")]
    return httpx.Response(200, content=json.dumps(body).encode(), headers=headers)


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(gw, "_client", httpx.AsyncClient(transport=httpx.MockTransport(_echo)))

    async def fake_jwks():
        return {"keys": [get_jwks_from_public_key(PUBLIC_PEM, KID)]}

    monkeypatch.setattr(gw, "get_jwks", fake_jwks)
    return TestClient(gw.app)


def test_listing_insights_route_to_ai_service(client):
    data = client.get("/api/v1/houses/7/insights").json()
    assert data["host"] == "ai-insights-service"
    assert data["path"] == "/api/v1/houses/7/insights"


def test_listing_reads_route_to_house_service(client):
    assert client.get("/api/v1/houses/7").json()["host"] == "house-api-service"
    assert client.get("/api/v1/houses/search?q=x").json()["host"] == "house-api-service"


def test_neighbourhood_and_cashflow_are_public(client):
    assert client.get("/api/v1/neighborhoods/toronto/annex/analysis").status_code == 200
    assert client.post("/api/v1/cashflow", json={}).status_code == 200


def test_client_supplied_identity_headers_are_stripped(client):
    """A caller must not be able to impersonate a user by sending X-User-ID."""
    data = client.get(
        "/api/v1/houses/7", headers={"X-User-ID": "1", "X-User-Role": "admin"}
    ).json()
    assert data["x_user_id"] is None
    assert data["x_user_role"] is None


def test_identity_is_injected_from_token(client):
    data = client.get(
        "/api/v1/portfolio/saved", headers={"Authorization": f"Bearer {_token('user')}"}
    ).json()
    assert data["x_user_id"] == "42"
    assert data["x_user_role"] == "user"


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/v1/houses"),
        ("PUT", "/api/v1/houses/7"),
        ("DELETE", "/api/v1/houses/7"),
        ("POST", "/api/v1/scraper/jobs"),
        ("GET", "/api/v1/scraper/status"),
    ],
)
def test_admin_routes_reject_regular_users(client, method, path):
    anon = client.request(method, path)
    assert anon.status_code == 401

    user = client.request(method, path, headers={"Authorization": f"Bearer {_token('user')}"})
    assert user.status_code == 403

    admin = client.request(method, path, headers={"Authorization": f"Bearer {_token('admin')}"})
    assert admin.status_code == 200


def test_invalid_token_rejected_on_protected_route(client):
    response = client.get("/api/v1/portfolio/saved", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


def test_invalid_token_ignored_on_public_route(client):
    response = client.get("/api/v1/houses", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 200


def test_multiple_set_cookie_headers_survive_proxy(client):
    response = client.post("/api/v1/auth/login", json={})
    cookies = response.headers.get_list("set-cookie")
    assert len(cookies) == 2
    assert {c.split("=")[0] for c in cookies} == {"access_token", "refresh_token"}


def test_unknown_route_is_404(client):
    assert client.get("/api/v1/nope").status_code == 404
