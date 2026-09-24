"""
NeighborIQ API — the single HTTP service.

Modules (one router each) keep their own boundaries: auth, listings, portfolio,
insights/markets and admin. Heavy or bursty work does not run here; it is
queued to the Celery workers (ingestion-worker, insights-worker), which scale
independently.
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.keys import load_signing_keys
from app.limits import limiter
from app.routers import admin, auth, insights, listings, portfolio
from shared import AsyncSessionLocal, dispose_db, init_db

logging.basicConfig(level=logging.INFO)
VERSION = "0.3.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as db:
        await load_signing_keys(db)
    yield
    await dispose_db()


app = FastAPI(
    title="NeighborIQ API",
    version=VERSION,
    description="Canadian residential investment analytics: listings, comparables, cash flow, markets.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()],
    allow_credentials=True,  # HttpOnly auth cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

for module in (auth, listings, portfolio, insights, admin):
    app.include_router(module.router)


@app.get("/health", tags=["health"])
@app.get("/api/v1/health", tags=["health"])
async def health():
    """Liveness plus a database round-trip."""
    db_ok = True
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "api",
        "version": VERSION,
        "database": "up" if db_ok else "down",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
