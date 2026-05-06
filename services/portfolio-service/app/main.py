"""
Portfolio Service - User-saved houses and portfolio management.

Provides endpoints for managing user-saved houses (portfolio/watchlist).
"""

from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload

# Import shared models first — registers House/User with Base before init_db runs
from shared import get_db, init_db, dispose_db
from shared.models import House as HouseModel, User as UserModel
from shared.models.schemas import HealthResponse

# Import local portfolio model after shared models so FK string refs resolve
from app.models import SavedHouse as SavedHouseModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await dispose_db()


app = FastAPI(
    title="NeighborIQ Portfolio Service",
    version="0.1.0",
    description="Portfolio/watchlist management for saved houses.",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Service health checks"},
        {"name": "portfolio", "description": "Portfolio management endpoints"},
    ],
)


# ============================================================================
# Health
# ============================================================================


@app.get("/health", tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="portfolio-service",
        version="0.1.0",
        timestamp=datetime.utcnow(),
    )


# ============================================================================
# Portfolio
# ============================================================================


class SaveHouseRequest(BaseModel):
    house_id: int
    notes: Optional[str] = None


def _get_user_id(request: Request) -> int:
    """Extract and validate user ID from X-User-ID header (injected by API gateway)."""
    user_id_str = request.headers.get("X-User-ID")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="User not authenticated")
    try:
        return int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID")


async def _verify_user(user_id: int, db: AsyncSession) -> UserModel:
    """Verify user exists."""
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/api/v1/portfolio/saved", tags=["portfolio"])
async def get_saved_houses(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get all saved houses for the current user."""
    user_id = _get_user_id(request)
    await _verify_user(user_id, db)

    result = await db.execute(
        select(SavedHouseModel)
        .where(SavedHouseModel.user_id == user_id)
        .options(joinedload(SavedHouseModel.house))
        .order_by(SavedHouseModel.created_at.desc())
    )
    saved_entries = result.unique().scalars().all()

    response_data = []
    for entry in saved_entries:
        house = entry.house
        response_data.append({
            "id": entry.id,
            "house_id": house.id,
            "saved_at": entry.created_at.isoformat(),
            "notes": entry.notes,
            "house": {
                "id": house.id,
                "title": house.title,
                "community": house.community,
                "city": house.city,
                "region": house.region,
                "street": house.street,
                "price": house.price,
                "area": float(house.area) if house.area else None,
                "rooms": house.rooms,
                "floor": house.floor,
                "decoration": house.decoration,
                "age": house.age,
                "latitude": float(house.latitude) if house.latitude else None,
                "longitude": float(house.longitude) if house.longitude else None,
                "url": house.url,
                "images": house.images,
                "created_at": house.created_at.isoformat(),
                "updated_at": house.updated_at.isoformat() if house.updated_at else None,
            },
        })

    return response_data


@app.post("/api/v1/portfolio/save", tags=["portfolio"])
async def save_house(
    request: Request,
    body: SaveHouseRequest,
    db: AsyncSession = Depends(get_db),
):
    """Save a house to the portfolio."""
    user_id = _get_user_id(request)
    await _verify_user(user_id, db)

    result = await db.execute(select(HouseModel).where(HouseModel.id == body.house_id))
    house = result.scalar_one_or_none()
    if not house:
        raise HTTPException(status_code=404, detail="House not found")

    result = await db.execute(
        select(SavedHouseModel).where(
            and_(
                SavedHouseModel.user_id == user_id,
                SavedHouseModel.house_id == body.house_id,
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return {"message": "House already saved", "id": existing.id}

    saved_house = SavedHouseModel(
        user_id=user_id,
        house_id=body.house_id,
        notes=body.notes,
    )
    db.add(saved_house)
    await db.commit()
    await db.refresh(saved_house)

    return {
        "message": "House saved successfully",
        "id": saved_house.id,
        "house_id": saved_house.house_id,
    }


@app.delete("/api/v1/portfolio/saved/{house_id}", tags=["portfolio"])
async def remove_house(
    request: Request,
    house_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Remove a house from the portfolio."""
    user_id = _get_user_id(request)
    await _verify_user(user_id, db)

    result = await db.execute(
        select(SavedHouseModel).where(
            and_(
                SavedHouseModel.user_id == user_id,
                SavedHouseModel.house_id == house_id,
            )
        )
    )
    saved_house = result.scalar_one_or_none()
    if not saved_house:
        raise HTTPException(status_code=404, detail="House not found in portfolio")

    await db.delete(saved_house)
    await db.commit()

    return {"message": "House removed from portfolio"}
