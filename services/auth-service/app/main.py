"""
Auth Service - Identity boundary for users, JWT tokens, and JWKS exposure.

Responsibilities:
- User registration and login
- RS256 JWT access/refresh token generation
- JWKS endpoint for other services to verify tokens
- Password hashing and storage
- Refresh token rotation
"""

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt as pyjwt
from fastapi import FastAPI, HTTPException, Depends, Response, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared import (
    get_db,
    init_db,
    dispose_db,
    User,
    JWTKeyPair,
    RefreshToken,
    UserCreate,
    UserLogin,
    UserResponse,
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_password,
    hash_password,
    generate_rsa_keypair,
    get_key_id,
    get_jwks_from_public_key,
    hash_token,
)
from shared.models.schemas import HealthResponse
from shared.utils.jwt_utils import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ============================================================================
# Startup/Shutdown Events
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.

    Startup:
    - Initialize database
    - Generate RS256 keys if not present

    Shutdown:
    - Dispose database connections
    """
    # Startup
    logger.info("Starting Auth Service...")
    await init_db()

    # Generate or load JWT keys
    async with get_db_session() as db:
        await initialize_jwt_keys(db)

    logger.info("Auth Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Auth Service...")
    await dispose_db()


@asynccontextmanager
async def get_db_session():
    """Async context manager for getting a database session in non-request code (e.g. lifespan)."""
    async for session in get_db():
        yield session


async def initialize_jwt_keys(db: AsyncSession):
    """
    Initialize RS256 keys.

    On first startup, generate a new key pair and store in the database.
    On subsequent startups, load the existing key pair and set environment variables.
    """
    # Check if keys already exist
    result = await db.execute(select(JWTKeyPair).where(JWTKeyPair.is_active == 1))
    existing_key = result.scalar_one_or_none()

    if existing_key:
        logger.info(f"Loaded existing JWT key: {existing_key.key_id}")
        os.environ["JWT_PRIVATE_KEY"] = existing_key.private_key_pem
        os.environ["JWT_PUBLIC_KEY"] = existing_key.public_key_pem
    else:
        logger.info("Generating new RS256 key pair...")
        private_key_pem, public_key_pem = generate_rsa_keypair()
        key_id = get_key_id(public_key_pem)

        new_key = JWTKeyPair(
            private_key_pem=private_key_pem,
            public_key_pem=public_key_pem,
            algorithm="RS256",
            key_id=key_id,
            is_active=1,
        )
        db.add(new_key)
        await db.commit()

        os.environ["JWT_PRIVATE_KEY"] = private_key_pem
        os.environ["JWT_PUBLIC_KEY"] = public_key_pem

        logger.info(f"Generated new JWT key: {key_id}")


# ============================================================================
# FastAPI App Setup
# ============================================================================

app = FastAPI(
    title="NeighborIQ Auth Service",
    version="0.1.0",
    description="Identity boundary for users, roles, RS256 JWT cookies, and JWKS exposure.",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Service health checks"},
        {"name": "auth", "description": "Authentication and identity endpoints"},
    ],
)


# ============================================================================
# Health Endpoint
# ============================================================================


@app.get("/health", tags=["health"], response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        service="auth-service",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
    )


# ============================================================================
# Auth Endpoints
# ============================================================================


@app.post("/api/v1/auth/signup", tags=["auth"], response_model=UserResponse)
async def signup(
    user_create: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.

    Request body:
    - email: EmailStr
    - password: str (min 8 chars)
    - name: Optional[str]

    Response:
    - Sets HttpOnly access_token and refresh_token cookies
    - Returns user info
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_create.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create new user
    new_user = User(
        email=user_create.email,
        name=user_create.name,
        password_hash=hash_password(user_create.password),
        role="user",
        is_active=1,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Generate tokens
    access_token = create_access_token(subject=str(new_user.id))
    refresh_token = create_refresh_token(subject=str(new_user.id))

    # Store refresh token hash (for revocation tracking)
    refresh_token_obj = RefreshToken(
        user_id=new_user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        is_revoked=0,
    )
    db.add(refresh_token_obj)
    await db.commit()

    # Set HttpOnly cookies
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=900,  # 15 minutes
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=604800,  # 7 days
    )

    return UserResponse.model_validate(new_user)


@app.post("/api/v1/auth/login", tags=["auth"], response_model=UserResponse)
async def login(
    user_login: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and issue tokens.

    Request body:
    - email: EmailStr
    - password: str

    Response:
    - Sets HttpOnly access_token and refresh_token cookies
    - Returns user info
    """
    # Find user
    result = await db.execute(select(User).where(User.email == user_login.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_login.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.is_active == 0:
        raise HTTPException(status_code=403, detail="User account is disabled")

    # Generate tokens
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    # Store refresh token hash
    refresh_token_obj = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        is_revoked=0,
    )
    db.add(refresh_token_obj)
    await db.commit()

    # Set HttpOnly cookies
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=900,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=604800,
    )

    return UserResponse.model_validate(user)


@app.post("/api/v1/auth/logout", tags=["auth"])
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """
    Logout user by revoking refresh token and clearing cookies.
    """
    # Extract the refresh token from cookies
    refresh_token = request.cookies.get("refresh_token")
    
    # Revoke the refresh token if it exists
    if refresh_token:
        # Hash the token to look up in database
        token_hash = hash_token(refresh_token)
        
        # Find and revoke the refresh token record
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash, RefreshToken.is_revoked == 0
            )
        )
        stored_token = result.scalar_one_or_none()
        
        if stored_token:
            stored_token.is_revoked = 1
            stored_token.revoked_at = datetime.now(timezone.utc)
            await db.commit()

    # Clear cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return {"status": "ok"}


@app.get("/api/v1/auth/me", tags=["auth"], response_model=UserResponse)
async def get_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get current authenticated user info.

    The API Gateway verifies the JWT and passes the user_id in the X-User-ID header.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-ID header")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_active == 0:
        raise HTTPException(status_code=403, detail="User account is disabled")

    return UserResponse.model_validate(user)


@app.post("/api/v1/auth/refresh", tags=["auth"])
async def refresh_access_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh an expired access token using the refresh token cookie.
    Implements refresh token rotation.
    """
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token cookie")

    # Hash the token to look up in database
    token_hash = hash_token(refresh_token)

    # Find the refresh token record
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash, RefreshToken.is_revoked == 0
        )
    )
    stored_token = result.scalar_one_or_none()

    if not stored_token:
        raise HTTPException(status_code=401, detail="Invalid or revoked refresh token")

    # Verify the JWT token (checks expiration and type)
    try:
        payload = verify_token(refresh_token, token_type="refresh")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Revoke the current refresh token (token rotation)
    stored_token.is_revoked = 1
    stored_token.revoked_at = datetime.now(timezone.utc)
    await db.commit()

    # Create new access and refresh tokens
    user_id = payload["sub"]
    new_access_token = create_access_token(subject=user_id)
    new_refresh_token = create_refresh_token(subject=user_id)

    # Store the new refresh token hash
    new_refresh_token_obj = RefreshToken(
        user_id=int(user_id),
        token_hash=hash_token(new_refresh_token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        is_revoked=0,
    )
    db.add(new_refresh_token_obj)
    await db.commit()

    # Set cookies for the new tokens
    response.set_cookie(
        "access_token",
        new_access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert minutes to seconds
    )
    response.set_cookie(
        "refresh_token",
        new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # Convert days to seconds
    )

    return {"status": "ok"}


@app.get("/api/v1/auth/.well-known/jwks.json", tags=["auth"])
async def get_jwks(db: AsyncSession = Depends(get_db)):
    """
    Return the JWKS (JSON Web Key Set) containing the public key.

    This endpoint is used by other services to verify JWT tokens offline.
    The API Gateway fetches and caches this public key, verifying all incoming JWTs
    without making a round-trip to the auth service.
    """
    # Fetch active key
    result = await db.execute(select(JWTKeyPair).where(JWTKeyPair.is_active == 1))
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(status_code=500, detail="No active JWT key found")

    # Convert to JWKS format
    jwk = get_jwks_from_public_key(key.public_key_pem, key.key_id)

    return {"keys": [jwk]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
