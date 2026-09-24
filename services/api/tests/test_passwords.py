"""Password hashing: Argon2id for new hashes, legacy bcrypt accepted and upgraded on login."""

import os
import uuid

import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from app.passwords import hash_password, verify_password


def _legacy_bcrypt(password: str) -> str:
    """What passlib + bcrypt stored in earlier releases (input truncated to 72 bytes)."""
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt(rounds=4)).decode()


def test_new_hashes_are_argon2id():
    hashed = hash_password("correct horse battery staple")
    assert hashed.startswith("$argon2id$")
    assert verify_password("correct horse battery staple", hashed) == (True, None)
    assert verify_password("wrong", hashed) == (False, None)


def test_legacy_bcrypt_verifies_and_asks_for_upgrade():
    legacy = _legacy_bcrypt("s3cret-password")
    ok, new_hash = verify_password("s3cret-password", legacy)
    assert ok and new_hash.startswith("$argon2id$")
    assert verify_password("not-it", legacy) == (False, None)


def test_legacy_passwords_longer_than_72_bytes_still_work():
    long_password = "p" * 100
    ok, _ = verify_password(long_password, _legacy_bcrypt(long_password))
    assert ok


def test_login_upgrades_a_legacy_hash(client):
    # Own client: the shared one must not carry this user's session cookies into other tests
    own = TestClient(app)
    email = f"legacy_{uuid.uuid4().hex[:8]}@example.com"
    assert (
        own.post("/api/v1/auth/signup", json={"email": email, "password": "legacy-password"}).status_code
        == 200
    )

    engine = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2"))
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE auth_users SET password_hash = :h WHERE email = :e"),
            {"h": _legacy_bcrypt("legacy-password"), "e": email},
        )

    r = own.post("/api/v1/auth/login", json={"email": email, "password": "legacy-password"})
    assert r.status_code == 200, r.text
    with engine.connect() as conn:
        stored = conn.execute(
            text("SELECT password_hash FROM auth_users WHERE email = :e"), {"e": email}
        ).scalar()
    assert stored.startswith("$argon2id$")
    engine.dispose()
