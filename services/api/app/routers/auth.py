"""
Identity: signup, login, logout, token refresh, current user, JWKS.

Access tokens (15 min) and refresh tokens (7 days) are RS256 JWTs delivered as
HttpOnly cookies. Refresh tokens rotate on every use and are revocable (only a
hash is stored).
"""

import os
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.keys import keys
from app.limits import limiter
from app.passwords import hash_password, verify_password
from app.schemas import UserCreate, UserLogin, UserResponse
from app.security import CurrentUser, current_user
from app.tokens import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    get_jwks_from_public_key,
    hash_token,
    verify_token,
)
from shared import RefreshToken, User, get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Secure cookies require HTTPS — browsers treat http://localhost as secure
SECURE_COOKIES: bool = os.environ.get("SECURE_COOKIES", "1").strip() == "1"
# Bootstrap operators: accounts signing up with these emails get role=admin.
ADMIN_EMAILS: set[str] = {
    e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()
}


# Brute-force protection on credential endpoints
AUTH_RATE_LIMIT = os.environ.get("AUTH_RATE_LIMIT", "10/minute")


def _role(user: User) -> str:
    """Role string for the JWT claim (column is an Enum on Postgres, str on SQLite)."""
    return getattr(user.role, "value", user.role) or "user"


async def _issue_tokens(response: Response, db: AsyncSession, user: User) -> None:
    """Mint an access + refresh pair, record the refresh hash, set both cookies."""
    access = create_access_token(
        subject=str(user.id), role=_role(user), private_key_pem=keys.private_pem, key_id=keys.key_id
    )
    refresh = create_refresh_token(subject=str(user.id), private_key_pem=keys.private_pem, key_id=keys.key_id)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            is_revoked=0,
        )
    )
    await db.commit()
    for name, value, max_age in (
        ("access_token", access, ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        ("refresh_token", refresh, REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600),
    ):
        response.set_cookie(
            name, value, httponly=True, secure=SECURE_COOKIES, samesite="strict", max_age=max_age
        )


@router.post("/signup", response_model=UserResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def signup(
    request: Request, user_create: UserCreate, response: Response, db: AsyncSession = Depends(get_db)
):
    """Register a new user and sign them in."""
    if (await db.execute(select(User).where(User.email == user_create.email))).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=user_create.email,
        name=user_create.name,
        password_hash=hash_password(user_create.password),
        role="admin" if user_create.email.lower() in ADMIN_EMAILS else "user",
        is_active=1,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await _issue_tokens(response, db, user)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=UserResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(
    request: Request, user_login: UserLogin, response: Response, db: AsyncSession = Depends(get_db)
):
    """Authenticate and set session cookies."""
    user = (await db.execute(select(User).where(User.email == user_login.email))).scalar_one_or_none()
    if not user or not verify_password(user_login.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.is_active == 0:
        raise HTTPException(status_code=403, detail="User account is disabled")
    await _issue_tokens(response, db, user)
    return UserResponse.model_validate(user)


@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Revoke the refresh token and clear cookies."""
    refresh = request.cookies.get("refresh_token")
    if refresh:
        stored = (
            await db.execute(
                select(RefreshToken).where(
                    RefreshToken.token_hash == hash_token(refresh), RefreshToken.is_revoked == 0
                )
            )
        ).scalar_one_or_none()
        if stored:
            stored.is_revoked = 1
            stored.revoked_at = datetime.now(UTC)
            await db.commit()
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"status": "ok"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: CurrentUser = Depends(current_user), db: AsyncSession = Depends(get_db)):
    record = (await db.execute(select(User).where(User.id == user.id))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="User not found")
    if record.is_active == 0:
        raise HTTPException(status_code=403, detail="User account is disabled")
    return UserResponse.model_validate(record)


@router.post("/refresh")
async def refresh_access_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Rotate the refresh token and issue a new access token."""
    refresh = request.cookies.get("refresh_token")
    if not refresh:
        raise HTTPException(status_code=401, detail="Missing refresh token cookie")

    stored = (
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_token(refresh), RefreshToken.is_revoked == 0
            )
        )
    ).scalar_one_or_none()
    if not stored:
        raise HTTPException(status_code=401, detail="Invalid or revoked refresh token")
    try:
        payload = verify_token(refresh, public_key_pem=keys.public_pem, token_type="refresh")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    user = (await db.execute(select(User).where(User.id == int(payload["sub"])))).scalar_one_or_none()
    if not user or user.is_active == 0:
        raise HTTPException(status_code=401, detail="User not found or disabled")

    stored.is_revoked = 1
    stored.revoked_at = datetime.now(UTC)
    await _issue_tokens(response, db, user)
    return {"status": "ok"}


@router.get("/.well-known/jwks.json")
async def get_jwks():
    """Public key for third parties that need to verify NeighborIQ tokens."""
    return {"keys": [get_jwks_from_public_key(keys.public_pem, keys.key_id)]}
