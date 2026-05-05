import sys
sys.path.insert(0, '/app')

from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api-gateway"}


def test_routes_contract() -> None:
    response = TestClient(app).get("/api/v1/routes")

    assert response.status_code == 200
    data = response.json()
    assert "/api/v1/auth" in data["routes"]
    assert "/api/v1/houses" in data["routes"]
    assert "/api/v1/search" in data["routes"]


def test_public_auth_routes_bypass_jwt() -> None:
    """Login and signup must not be blocked by the JWT middleware.

    The auth-service is not running in unit tests, so the proxy call will fail
    with a connection error (5xx). We verify the gateway did NOT return 401
    (which would mean it blocked the request before forwarding).
    """
    # raise_server_exceptions=False converts connection errors to 5xx instead of raising
    client = TestClient(app, raise_server_exceptions=False)
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "x@x.com", "password": "pass"},
    )
    # Gateway must NOT reject a public auth route with "Missing access token" (401).
    # If it returns 401, it must be from the backend (Invalid email or password).
    # If the backend is down, it might return 5xx. Both prove bypass.
    if login_response.status_code == 401:
        assert login_response.json()["detail"] != "Missing access token"
    else:
        # If it's not 401, it should be 5xx (backend connection error in test) or 2xx/4xx (backend responded)
        # Any of these indicate the request passed through the gateway middleware
        assert login_response.status_code != 401


def test_protected_route_without_token_returns_401() -> None:
    """Requests to protected routes without a JWT must be rejected at the gateway."""
    response = TestClient(app).get("/api/v1/houses/1")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing access token"


def test_cors_preflight_allowed_origin() -> None:
    """OPTIONS preflight from the allowed origin must return CORS headers."""
    response = TestClient(app).options(
        "/api/v1/houses",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    # 200 (with CORS headers) — middleware handles preflight before JWT middleware
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_preflight_disallowed_origin() -> None:
    """OPTIONS preflight from an unknown origin must NOT echo that origin back."""
    response = TestClient(app).options(
        "/api/v1/houses",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # The CORS middleware must not reflect an unknown origin
    assert response.headers.get("access-control-allow-origin") != "https://evil.example.com"
