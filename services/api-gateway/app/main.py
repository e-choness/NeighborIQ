"""
API Gateway Service - Boundary for authentication, authorization, rate limiting, and routing.

Every /api/v1/* request is resolved against ROUTES to an upstream service and an
access policy:

  public — no token required (a valid token is still decoded if present)
  user   — valid access token required
  admin  — valid access token with role=admin required

Identity is forwarded downstream as X-User-ID / X-User-Role. Any client-supplied
X-User-* header is stripped first, so downstream services can trust these headers
as long as they are only reachable through the gateway (see docker-compose.yml:
internal services publish no host ports).
"""

import os
import re
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, Optional

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

# One pooled client for every upstream call.
_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0))


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await _client.aclose()


app = FastAPI(
    title="NeighborIQ API Gateway",
    version="0.2.0",
    description="Reverse proxy boundary for authentication, authorization, rate limiting, and routing.",
    lifespan=lifespan,
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
PORTFOLIO_SERVICE_URL = os.getenv("PORTFOLIO_SERVICE_URL", "http://portfolio-service:8000")
AI_INSIGHTS_SERVICE_URL = os.getenv("AI_INSIGHTS_SERVICE_URL", "http://ai-insights-service:8000")
SCRAPER_SERVICE_URL = os.getenv("SCRAPER_SERVICE_URL", "http://scraper-service:8000")

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

    try:
        response = await _client.get(
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
        raise HTTPException(status_code=503, detail=f"Unable to fetch JWKS: {str(e)}")


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


# ============================================================================
# Routing table
# ============================================================================

PUBLIC, USER, ADMIN = "public", "user", "admin"


@dataclass(frozen=True)
class Route:
    pattern: re.Pattern
    upstream: str
    read_policy: str  # GET/HEAD
    write_policy: str  # everything else


def _r(pattern: str, upstream: str, read: str, write: str) -> Route:
    return Route(re.compile(pattern), upstream, read, write)


# First match wins — keep specific patterns above their prefixes.
ROUTES: list[Route] = [
    # Auth: login/signup/refresh/logout/jwks are public, everything else needs a token
    _r(r"^/api/v1/auth/(login|signup|refresh|logout|\.well-known/jwks\.json)$",
       AUTH_SERVICE_URL, PUBLIC, PUBLIC),
    _r(r"^/api/v1/auth/", AUTH_SERVICE_URL, USER, USER),
    # Per-listing analytics live in ai-insights-service
    _r(r"^/api/v1/houses/\d+/(insights|valuation)$", AI_INSIGHTS_SERVICE_URL, PUBLIC, ADMIN),
    _r(r"^/api/v1/(neighborhoods|markets)(/|$)", AI_INSIGHTS_SERVICE_URL, PUBLIC, ADMIN),
    # Stateless calculator — the POST body carries only the user's assumptions
    _r(r"^/api/v1/cashflow$", AI_INSIGHTS_SERVICE_URL, PUBLIC, PUBLIC),
    _r(r"^/api/v1/ai/", AI_INSIGHTS_SERVICE_URL, ADMIN, ADMIN),
    # Listing catalogue: public reads, admin-only writes
    _r(r"^/api/v1/(houses|communities)(/|$)", HOUSE_SERVICE_URL, PUBLIC, ADMIN),
    _r(r"^/api/v1/search(/|$)", SEARCH_SERVICE_URL, PUBLIC, ADMIN),
    _r(r"^/api/v1/portfolio/", PORTFOLIO_SERVICE_URL, USER, USER),
    # Ingestion control is an operator function
    _r(r"^/api/v1/scraper/", SCRAPER_SERVICE_URL, ADMIN, ADMIN),
]


def resolve_route(path: str) -> Optional[Route]:
    for route in ROUTES:
        if route.pattern.match(path):
            return route
    return None


def policy_for(route: Route, method: str) -> str:
    return route.read_policy if method in ("GET", "HEAD") else route.write_policy


_HEALTH_PATH = re.compile(r"^/api/v1/[a-z]+/health$")


# ============================================================================
# Authentication / authorization middleware
# ============================================================================


def _extract_token(request: Request) -> Optional[str]:
    token = request.cookies.get("access_token")
    if token:
        return token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


async def _decode(token: str) -> dict:
    jwks_data = await get_jwks()
    public_key_pem = get_signing_key_from_jwks(jwks_data, token)
    return verify_token(token, public_key_pem=public_key_pem, token_type="access")


@app.middleware("http")
async def verify_jwt_middleware(request: Request, call_next):
    """Authenticate the caller and enforce the route's access policy."""
    path = request.url.path

    if (
        request.method == "OPTIONS"
        or path in ("/health", "/api/v1/routes")
        or _HEALTH_PATH.match(path)
        or path.startswith("/docs")
        or path.startswith("/openapi.json")
    ):
        return await call_next(request)

    route = resolve_route(path)
    if route is None:
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    policy = policy_for(route, request.method)

    token = _extract_token(request)
    error: Optional[JSONResponse] = None
    if token:
        try:
            payload = await _decode(token)
            request.state.user_id = payload["sub"]
            request.state.user_role = payload.get("role", "user")
        except HTTPException as e:
            error = JSONResponse(status_code=e.status_code, content={"detail": e.detail})
        except pyjwt.InvalidTokenError as e:
            error = JSONResponse(status_code=401, content={"detail": f"Invalid token: {str(e)}"})
        except Exception as e:
            error = JSONResponse(
                status_code=401, content={"detail": f"Token verification failed: {str(e)}"}
            )

    if policy != PUBLIC:
        if error is not None:
            return error
        if not hasattr(request.state, "user_id"):
            # Return JSONResponse directly — raising HTTPException from middleware is
            # unreliable across Starlette versions; a direct Response is always safe.
            return JSONResponse(status_code=401, content={"detail": "Missing access token"})
        if policy == ADMIN and request.state.user_role != "admin":
            return JSONResponse(status_code=403, content={"detail": "Admin role required"})

    return await call_next(request)


# ============================================================================
# Proxy
# ============================================================================

# RFC 7230 hop-by-hop headers plus headers httpx recomputes itself.
_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}
# httpx transparently decompresses, so the upstream encoding no longer applies.
_RESPONSE_DROP = _HOP_BY_HOP | {"content-encoding"}


def _forward_headers(request: Request) -> dict[str, str]:
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP and not k.lower().startswith("x-user-")
    }
    if hasattr(request.state, "user_id"):
        headers["X-User-ID"] = str(request.state.user_id)
        headers["X-User-Role"] = str(request.state.user_role)
    return headers


def _to_response(resp: httpx.Response) -> Response:
    out = Response(content=resp.content, status_code=resp.status_code)
    # Iterate raw pairs so repeated headers (Set-Cookie for access + refresh) survive;
    # dict(resp.headers) would comma-join them into one unparseable cookie.
    for key, value in resp.headers.multi_items():
        if key.lower() not in _RESPONSE_DROP:
            out.headers.append(key, value)
    return out


async def proxy(request: Request, upstream: str) -> Response:
    try:
        resp = await _client.request(
            method=request.method,
            url=f"{upstream}{request.url.path}",
            headers=_forward_headers(request),
            content=await request.body(),
            params=request.query_params,
        )
    except httpx.HTTPError as e:
        return JSONResponse(status_code=502, content={"detail": f"Upstream unavailable: {e}"})
    return _to_response(resp)


# ============================================================================
# Gateway endpoints
# ============================================================================


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "api-gateway"}


@app.get("/api/v1/routes", tags=["gateway"])
async def routes() -> dict[str, list[str]]:
    return {"routes": [
        "/api/v1/auth", "/api/v1/houses", "/api/v1/communities", "/api/v1/search",
        "/api/v1/portfolio", "/api/v1/neighborhoods", "/api/v1/cashflow",
        "/api/v1/ai", "/api/v1/scraper",
    ]}


_HEALTH_UPSTREAMS = {
    "admin": f"{AUTH_SERVICE_URL}/health",
    "auth": f"{AUTH_SERVICE_URL}/health",
    "houses": f"{HOUSE_SERVICE_URL}/health",
    "ai": f"{AI_INSIGHTS_SERVICE_URL}/api/v1/health",
    "search": f"{SEARCH_SERVICE_URL}/health",
    "portfolio": f"{PORTFOLIO_SERVICE_URL}/health",
    "scraper": f"{SCRAPER_SERVICE_URL}/api/v1/scraper/health",
}


@app.get("/api/v1/{service}/health", tags=["health"])
async def service_health(service: str) -> Response:
    """Proxy a downstream service's health check (used by the admin dashboard)."""
    url = _HEALTH_UPSTREAMS.get(service)
    if url is None:
        return JSONResponse(status_code=404, content={"detail": "Unknown service"})
    try:
        resp = await _client.get(url, timeout=3.0)
    except httpx.HTTPError as e:
        return JSONResponse(status_code=503, content={"status": "down", "detail": str(e)})
    return _to_response(resp)


@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@limiter.limit("100/minute")
async def gateway_proxy(request: Request, path: str) -> Response:
    """Forward to the upstream resolved from the routing table."""
    route = resolve_route(request.url.path)
    if route is None:
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return await proxy(request, route.upstream)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
