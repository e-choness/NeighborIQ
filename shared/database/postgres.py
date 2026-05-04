"""
Shared PostgreSQL database configuration and session management.

All services use a single PostgreSQL instance with domain-prefixed tables.
Domain prefixes (e.g., auth_, house_, portfolio_) maintain logical separation.
"""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

# Environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://root:root@localhost:5432/house_discovery",
)

# Create async engine
# NullPool: don't pool connections in development (simpler; each request gets fresh connection)
# QueuePool would be used in production
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL logging
    poolclass=NullPool,  # Disable pooling for dev
    connect_args={
        "timeout": 30,
        "command_timeout": 30,
        "server_settings": {
            "jit": "off",  # Disable JIT compilation
        },
    },
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Base class for all SQLAlchemy models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to inject database session into route handlers.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database: create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_db():
    """Dispose of engine (cleanup on shutdown)."""
    await engine.dispose()
