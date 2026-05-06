"""
API Gateway Service - Boundary for authentication, rate limiting, and routing.
"""

import os
import time
from typing import Any, Dict

import httpx
import jwt as pyjwt
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Import only JWT utilities — avoid pulling in the database layer (sqlalchemy/asyncpg)
# which the gateway does not need and does not install
from shared.utils.jwt_utils import verify_token

app = FastAPI(
    title="NeighborIQ API Gateway",
    version="0.1.0",
    description="Reverse proxy boundary for authentication, rate limiting, and routing.",
    openapi_tags=[
        {"name": "health", "description": "Service health checks"},
        {"name": "gateway", "description": "Gateway routing contract"},
    ],
)

# CORS — allow only the configured frontend origin (Phase 1D requirement)
# Defaults to the Vue 3 dev server; override via CORS_ORIGINS env var in production
_cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,  # Required so browsers send HttpOnly cookies cross-origin
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Service URLs
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
HOUSE_SERVICE_URL = os.getenv("HOUSE_SERVICE_URL", "http://house-api-service:8000")
SEARCH_SERVICE_URL = os.getenv("SEARCH_SERVICE_URL", "http://search-service:8000")

# Cache for JWKS (public key)
_jwks_cache = None
_jwks_cache_time = 0
JWKS_CACHE_TTL = 300  # 5 minutes


async def get_jwks():
    """Fetch and cache JWKS from auth service."""
    global _jwks_cache, _jwks_cache_time

    now = time.time()
    if _jwks_cache is not None and (now - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/api/v1/auth/.well-known/jwks.json"
            )
            response.raise_for_status()
            jwks_data = response.json()

            _jwks_cache = jwks_data
            _jwks_cache_time = now
            return jwks_data
        except Exception as e:
            # If we have cached data, use it even if expired
            if _jwks_cache is not None:
                return _jwks_cache
            raise HTTPException(
                status_code=503, detail=f"Unable to fetch JWKS: {str(e)}"
            )


def get_signing_key_from_jwks(jwks_data: Dict[str, Any], token: str) -> str:
    """Extract the appropriate public key from JWKS for token verification."""
    try:
        # Decode token header to get key ID
        header = pyjwt.get_unverified_header(token)
        kid = header.get("kid")

        if not kid:
            # If no kid in header, use the first key
            key_data = jwks_data["keys"][0]
        else:
            # Find key matching kid
            key_data = None
            for key in jwks_data["keys"]:
                if key.get("kid") == kid:
                    key_data = key
                    break

            if not key_data:
                # Fallback to first key
                key_data = jwks_data["keys"][0]

        # Convert JWK to PEM format
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import base64

        def base64url_to_int(s: str) -> int:
            s = s.replace("-", "+").replace("_", "/")
            padding = 4 - len(s) % 4
            if padding != 4:
                s += "=" * padding
            return int.from_bytes(base64.b64decode(s), "big")

        n = base64url_to_int(key_data["n"])
        e = base64url_to_int(key_data["e"])

        public_numbers = rsa.RSAPublicNumbers(e, n)
        public_key = public_numbers.public_key()

        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        return public_key_pem
    except Exception as e:
        raise HTTPException(
            status_code=401, detail=f"Unable to extract signing key: {str(e)}"
        )


# Public auth endpoints that do not require a JWT (login/signup generate tokens;
# refresh uses refresh cookie; jwks is the public key endpoint; logout clears cookies)
_PUBLIC_AUTH_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/signup",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
    "/api/v1/auth/.well-known/jwks.json",
}

# Public read-only routes — accessible without authentication (Phase 6: public search)
_PUBLIC_READ_PREFIXES = (
    "/api/v1/houses",
    "/api/v1/communities",
    "/api/v1/search",
)


@app.middleware("http")
async def verify_jwt_middleware(request: Request, call_next):
    """Middleware to verify JWT tokens for protected routes."""
    path = request.url.path

    # Skip verification for OPTIONS preflight (CORS), health, gateway info, docs, and public auth
    if (
        request.method == "OPTIONS"
        or path in ["/health", "/api/v1/routes"]
        or path in _PUBLIC_AUTH_PATHS
        or path.startswith("/docs")
        or path.startswith("/openapi.json")
    ):
        return await call_next(request)

    # Allow unauthenticated GET requests to public read-only endpoints (Phase 6 search page)
    if request.method == "GET" and any(path.startswith(p) for p in _PUBLIC_READ_PREFIXES):
        return await call_next(request)

    # Get token from cookie
    token = request.cookies.get("access_token")
    if not token:
        # Also check Authorization header as fallback
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        # Return JSONResponse directly — raising HTTPException from middleware is unreliable
        # across Starlette versions; a direct Response is always safe.
        return JSONResponse(status_code=401, content={"detail": "Missing access token"})

    try:
        # Get JWKS and verify token
        jwks_data = await get_jwks()
        public_key_pem = get_signing_key_from_jwks(jwks_data, token)

        # Verify token
        payload = verify_token(
            token, public_key_pem=public_key_pem, token_type="access"
        )

        # Store user info in request.state — proxy functions inject this into outgoing headers
        request.state.user_id = payload["sub"]
        request.state.user_email = payload.get("email", "")

    except pyjwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "Token has expired"})
    except pyjwt.InvalidTokenError as e:
        return JSONResponse(
            status_code=401, content={"detail": f"Invalid token: {str(e)}"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=401, content={"detail": f"Token verification failed: {str(e)}"}
        )

    response = await call_next(request)
    return response


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "api-gateway"}


@app.get("/api/v1/routes", tags=["gateway"])
async def routes() -> dict[str, list[str]]:
    return {"routes": ["/api/v1/auth", "/api/v1/houses", "/api/v1/search"]}


@app.api_route(
    "/api/v1/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
@limiter.limit("100/minute")
async def auth_proxy(request: Request, path: str):
    """Proxy requests to auth service."""
    async with httpx.AsyncClient() as client:
        url = f"{AUTH_SERVICE_URL}/api/v1/auth/{path}"
        headers = dict(request.headers)
        headers.pop("host", None)
        # Inject authenticated user ID for downstream use (e.g. /me endpoint)
        if hasattr(request.state, "user_id"):
            headers["X-User-ID"] = str(request.state.user_id)

        body = await request.body()

        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=request.query_params,
        )

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            media_type=resp.headers.get("content-type"),
        )


@app.api_route(
    "/api/v1/houses", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
@app.api_route(
    "/api/v1/houses/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
@limiter.limit("100/minute")
async def houses_proxy(request: Request, path: str = ""):
    """Proxy requests to house service."""
    async with httpx.AsyncClient() as client:
        url = f"{HOUSE_SERVICE_URL}/api/v1/houses/{path}".rstrip("/")
        headers = dict(request.headers)
        headers.pop("host", None)
        if hasattr(request.state, "user_id"):
            headers["X-User-ID"] = str(request.state.user_id)

        body = await request.body()

        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=request.query_params,
        )

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            media_type=resp.headers.get("content-type"),
        )


@app.api_route(
    "/api/v1/communities", methods=["GET"]
)
@app.api_route(
    "/api/v1/communities/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
@limiter.limit("100/minute")
async def communities_proxy(request: Request, path: str = ""):
    """Proxy community requests to house service."""
    async with httpx.AsyncClient() as client:
        url = f"{HOUSE_SERVICE_URL}/api/v1/communities/{path}".rstrip("/")
        headers = dict(request.headers)
        headers.pop("host", None)
        if hasattr(request.state, "user_id"):
            headers["X-User-ID"] = str(request.state.user_id)

        body = await request.body()
        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=request.query_params,
        )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            media_type=resp.headers.get("content-type"),
        )


@app.api_route(
    "/api/v1/search/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
@limiter.limit("100/minute")
async def search_proxy(request: Request, path: str):
    """Proxy requests to search service."""
    async with httpx.AsyncClient() as client:
        url = f"{SEARCH_SERVICE_URL}/api/v1/search/{path}"
        headers = dict(request.headers)
        headers.pop("host", None)
        if hasattr(request.state, "user_id"):
            headers["X-User-ID"] = str(request.state.user_id)

        # Get request body
        body = await request.body()

        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=request.query_params,
        )

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            media_type=resp.headers.get("content-type"),
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
