"""Identity: signup/login/refresh/logout, role claim and admin bootstrap."""

import uuid

import jwt as pyjwt
from fastapi.testclient import TestClient

from app.main import app


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _claims(c: TestClient) -> dict:
    return pyjwt.decode(c.cookies["access_token"], options={"verify_signature": False})


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["database"] == "up"


def test_jwks_contract(client: TestClient) -> None:
    keys = client.get("/api/v1/auth/.well-known/jwks.json").json()["keys"]
    assert len(keys) == 1 and keys[0]["kty"] == "RSA"


def test_login_invalid_credentials_returns_401(client: TestClient) -> None:
    r = client.post("/api/v1/auth/login", json={"email": "notfound@example.com", "password": "wrongpassword"})
    assert r.status_code == 401
    assert "access_token" not in r.cookies


def test_signup_missing_body_returns_422(client: TestClient) -> None:
    assert client.post("/api/v1/auth/signup", json={}).status_code == 422


def test_duplicate_signup_409(client: TestClient) -> None:
    email = _email("dup")
    with TestClient(app) as c:
        assert (
            c.post("/api/v1/auth/signup", json={"email": email, "password": "secure_password123"}).status_code
            == 200
        )
        assert (
            c.post("/api/v1/auth/signup", json={"email": email, "password": "secure_password123"}).status_code
            == 409
        )


def test_signup_login_me_roundtrip() -> None:
    email = _email("me")
    with TestClient(app) as c:
        c.post("/api/v1/auth/signup", json={"email": email, "password": "secure_password123", "name": "Me"})
        assert _claims(c)["role"] == "user"
        me = c.get("/api/v1/auth/me").json()
        assert me["email"] == email and me["role"] == "user"
    with TestClient(app) as c:
        assert (
            c.post("/api/v1/auth/login", json={"email": email, "password": "secure_password123"}).status_code
            == 200
        )
        assert c.get("/api/v1/auth/me").status_code == 200


def test_me_requires_token(client: TestClient) -> None:
    with TestClient(app) as c:
        assert c.get("/api/v1/auth/me").status_code == 401


def test_refresh_rotates_and_logout_revokes() -> None:
    with TestClient(app) as c:
        c.post("/api/v1/auth/signup", json={"email": _email("rot"), "password": "secure_password123"})
        first = c.cookies["refresh_token"]
        assert c.post("/api/v1/auth/refresh").status_code == 200
        assert c.cookies["refresh_token"] != first

        assert c.post("/api/v1/auth/logout").json()["status"] == "ok"
        after = c.post("/api/v1/auth/refresh")
        assert after.status_code == 401


def test_reused_refresh_token_rejected() -> None:
    with TestClient(app) as c:
        c.post("/api/v1/auth/signup", json={"email": _email("reuse"), "password": "secure_password123"})
        stolen = c.cookies["refresh_token"]
        assert c.post("/api/v1/auth/refresh").status_code == 200
    with TestClient(app) as attacker:
        attacker.cookies.set("refresh_token", stolen)
        assert attacker.post("/api/v1/auth/refresh").status_code == 401


def test_admin_emails_bootstrap_admin_role() -> None:
    from app.routers import auth

    email = _email("boot")
    auth.ADMIN_EMAILS.add(email)
    with TestClient(app) as c:
        r = c.post("/api/v1/auth/signup", json={"email": email, "password": "secure_password123"})
        assert r.json()["role"] == "admin" and _claims(c)["role"] == "admin"
        assert c.post("/api/v1/auth/refresh").status_code == 200
        assert _claims(c)["role"] == "admin"
