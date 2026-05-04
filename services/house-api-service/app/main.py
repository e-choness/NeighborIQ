from contextlib import asynccontextmanager
from decimal import Decimal
from uuid import UUID
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from pydantic import BaseModel, Field

from shared import get_db, House, Community, HousePriceHistory, init_db, dispose_db
from shared.models.schemas import HouseResponse, HouseListResponse, CommunityResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await dispose_db()


app = FastAPI(
    title="NeighborIQ House API Service",
    version="0.1.0",
    description="House, community, and POI read/write contract for discovery workflows.",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Service health checks"},
        {"name": "houses", "description": "House discovery contract"},
        {"name": "communities", "description": "Community contract"},
    ],
)


# ============================================================================
# Health
# ============================================================================

@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "house-api-service"}


# ============================================================================
# Houses
# ============================================================================

@app.get("/api/v1/houses", tags=["houses"])
async def list_houses(
    city: Optional[str] = Query(default=None, description="Filter by city"),
    region: Optional[str] = Query(default=None, description="Filter by region"),
    street: Optional[str] = Query(default=None, description="Filter by street"),
    community: Optional[str] = Query(default=None, description="Filter by community"),
    price_min: Optional[int] = Query(default=None, description="Minimum price (yuan)"),
    price_max: Optional[int] = Query(default=None, description="Maximum price (yuan)"),
    rooms_min: Optional[int] = Query(default=None, description="Minimum number of rooms"),
    rooms_max: Optional[int] = Query(default=None, description="Maximum number of rooms"),
    area_min: Optional[Decimal] = Query(default=None, description="Minimum area (sqm)"),
    area_max: Optional[Decimal] = Query(default=None, description="Maximum area (sqm)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=100, description="Page size"),
    sort: str = Query(default="created_at", description="Sort field (price, created_at, area)"),
    order: str = Query(default="desc", description="Sort order (asc, desc)"),
    db: AsyncSession = Depends(get_db),
) -> HouseListResponse:
    """
    List houses with filtering and pagination.
    
    Filters:
    - Geographic: city, region, street, community
    - Price range: price_min, price_max
    - Property: rooms, area
    
    Returns paginated results.
    """
    # Build shared filter conditions
    conditions = [House.is_active == 1]
    if city:
        conditions.append(House.city == city)
    if region:
        conditions.append(House.region == region)
    if street:
        conditions.append(House.street.contains(street))
    if community:
        conditions.append(House.community.contains(community))
    if price_min is not None:
        conditions.append(House.price >= price_min)
    if price_max is not None:
        conditions.append(House.price <= price_max)
    if rooms_min is not None:
        conditions.append(House.rooms >= rooms_min)
    if rooms_max is not None:
        conditions.append(House.rooms <= rooms_max)
    if area_min is not None:
        conditions.append(House.area >= area_min)
    if area_max is not None:
        conditions.append(House.area <= area_max)

    # Count total using a dedicated scalar query (not add_columns which produces tuple rows)
    count_result = await db.execute(select(func.count(House.id)).where(*conditions))
    total = count_result.scalar() or 0

    # Build data query with the same conditions
    query = select(House).where(*conditions)

    # Apply sorting
    sort_field_map = {
        "price": House.price,
        "created_at": House.created_at,
        "area": House.area,
    }
    sort_field = sort_field_map.get(sort, House.created_at)
    if order == "desc":
        query = query.order_by(sort_field.desc())
    else:
        query = query.order_by(sort_field.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute
    result = await db.execute(query)
    houses = result.scalars().all()

    return HouseListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[HouseResponse.model_validate(h) for h in houses],
    )


@app.get("/api/v1/houses/{house_id}", tags=["houses"])
async def get_house(house_id: int, db: AsyncSession = Depends(get_db)) -> HouseResponse:
    """
    Get house details by ID.
    """
    result = await db.execute(
        select(House).where(House.id == house_id, House.is_active == 1)
    )
    house = result.scalar_one_or_none()
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    return HouseResponse.model_validate(house)


@app.post("/api/v1/houses", tags=["houses"])
async def create_house(
    house: HouseResponse,
    db: AsyncSession = Depends(get_db),
) -> HouseResponse:
    """
    Create a new house listing (admin only).
    """
    new_house = House(**house.model_dump(exclude={"id", "created_at", "updated_at"}))
    db.add(new_house)
    await db.commit()
    await db.refresh(new_house)
    return HouseResponse.model_validate(new_house)


@app.put("/api/v1/houses/{house_id}", tags=["houses"])
async def update_house(
    house_id: int,
    house_update: HouseResponse,
    db: AsyncSession = Depends(get_db),
) -> HouseResponse:
    """
    Update a house listing (admin only).
    """
    result = await db.execute(
        select(House).where(House.id == house_id, House.is_active == 1)
    )
    house = result.scalar_one_or_none()
    if not house:
        raise HTTPException(status_code=404, detail="House not found")

    for key, value in house_update.model_dump(exclude_unset=True).items():
        if hasattr(house, key):
            setattr(house, key, value)

    house.updated_at = datetime.now()
    await db.commit()
    await db.refresh(house)
    return HouseResponse.model_validate(house)


@app.delete("/api/v1/houses/{house_id}", tags=["houses"])
async def delete_house(
    house_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Soft-delete a house (admin only).
    """
    result = await db.execute(
        select(House).where(House.id == house_id, House.is_active == 1)
    )
    house = result.scalar_one_or_none()
    if not house:
        raise HTTPException(status_code=404, detail="House not found")

    house.is_active = 0
    house.updated_at = datetime.now()
    await db.commit()
    return {"status": "ok", "message": "House deactivated"}


# ============================================================================
# Search
# ============================================================================

@app.get("/api/v1/houses/search", tags=["houses"])
async def search_houses(
    q: Optional[str] = Query(default=None, description="Full-text search query"),
    city: Optional[str] = Query(default=None, description="Filter by city"),
    region: Optional[str] = Query(default=None, description="Filter by region"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search houses by keyword and filters.
    """
    query = select(House).where(House.is_active == 1)

    if q:
        search_pattern = f"%{q}%"
        query = query.where(
            or_(
                House.title.ilike(search_pattern),
                House.community.ilike(search_pattern),
                House.street.ilike(search_pattern),
            )
        )

    if city:
        query = query.where(House.city == city)
    if region:
        query = query.where(House.region == region)

    result = await db.execute(query.limit(50))
    houses = result.scalars().all()

    return {"items": [HouseResponse.model_validate(h) for h in houses]}


# ============================================================================
# Communities
# ============================================================================

@app.get("/api/v1/communities", tags=["communities"])
async def list_communities(
    city: Optional[str] = Query(default=None, description="Filter by city"),
    region: Optional[str] = Query(default=None, description="Filter by region"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    List communities with aggregated statistics.
    """
    query = select(Community).where(Community.house_count > 0)

    if city:
        query = query.where(Community.city == city)
    if region:
        query = query.where(Community.region == region)

    result = await db.execute(query)
    communities = result.scalars().all()

    return {
        "items": [
            CommunityResponse.model_validate(c) for c in communities
        ]
    }


@app.get("/api/v1/communities/{community_id}/stats", tags=["communities"])
async def get_community_stats(
    community_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get aggregated statistics for a community.
    """
    result = await db.execute(
        select(Community).where(Community.id == community_id)
    )
    community = result.scalar_one_or_none()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")

    # Get house stats
    house_query = select(
        func.count(House.id),
        func.avg(House.price),
        func.min(House.price),
        func.max(House.price),
        func.avg(House.area),
    ).where(
        and_(
            House.community == community.name,
            House.city == community.city,
            House.is_active == 1,
        )
    )

    house_result = await db.execute(house_query)
    house_stats = house_result.fetchone()

    return {
        "community": CommunityResponse.model_validate(community),
        "house_count": house_stats[0] or 0,
        "avg_price": float(house_stats[1]) if house_stats[1] else None,
        "min_price": house_stats[2],
        "max_price": house_stats[3],
        "avg_area": float(house_stats[4]) if house_stats[4] else None,
    }