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


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    """Test that logout endpoint properly revokes the refresh token."""
    # 1. Sign up a new user
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "logout_test@example.com",
            "password": "secure_password123",
            "name": "Logout Test User",
        },
    )
    assert response.status_code == 200
    assert "refresh_token" in client.cookies

    # 2. Verify the refresh token is valid by using it to refresh the access token
    refresh_response = client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200

    # 3. Call logout to revoke the token
    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json()["status"] == "ok"

    # 4. Try to use the refresh token after logout - should fail
    refresh_after_logout = client.post("/api/v1/auth/refresh")
    assert refresh_after_logout.status_code == 401
    detail = refresh_after_logout.json()["detail"].lower()
    assert "revoked" in detail or "invalid" in detail or "missing" in detail


def test_logout_clears_cookies(client: TestClient) -> None:
    """Test that logout clears the access and refresh token cookies."""
    # 1. Sign up a new user
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "logout_cookies_test@example.com",
            "password": "secure_password123",
            "name": "Logout Cookies Test",
        },
    )
    assert response.status_code == 200
    assert "refresh_token" in client.cookies

    # 2. Call logout
    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200

    # 3. Verify cookies are cleared (max_age=0 or expires in past)
    # The TestClient will have removed the cookies
    assert "refresh_token" not in client.cookies or client.cookies.get("refresh_token") == ""
