import sys
sys.path.insert(0, '/app')

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "auth-service"


def test_jwks_contract(client: TestClient) -> None:
    response = client.get("/api/v1/auth/.well-known/jwks.json")

    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert isinstance(data["keys"], list)
    assert len(data["keys"]) >= 1


def test_login_invalid_credentials_returns_401(client: TestClient) -> None:
    """Invalid credentials must return 401; no cookies should be set on failure."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "notfound@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert "access_token" not in response.cookies


def test_signup_missing_body_returns_422(client: TestClient) -> None:
    """Missing required fields must return 422 Unprocessable Entity."""
    response = client.post("/api/v1/auth/signup", json={})

    assert response.status_code == 422
