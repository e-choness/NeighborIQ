"""
Listing catalogue: search/filter, detail, price history, neighbourhood POIs,
communities, and admin-only writes.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    CommunityResponse,
    HouseCreate,
    HouseListResponse,
    HouseResponse,
    HouseUpdate,
    PricePoint,
)
from app.security import admin_user
from shared import Community, House, HousePriceHistory, HouseRentalYield, get_db

router = APIRouter(tags=["listings"])


# First recorded asking price — lets clients show "price cut from $X" badges
_ORIGINAL_PRICE = (
    select(HousePriceHistory.price)
    .where(HousePriceHistory.house_id == House.id)
    .order_by(HousePriceHistory.recorded_at.asc(), HousePriceHistory.id.asc())
    .limit(1)
    .correlate(House)
    .scalar_subquery()
)


# Unlevered yields computed by the insights worker (NULL until it has run)
_GROSS_YIELD = (
    select(HouseRentalYield.gross_yield)
    .where(HouseRentalYield.house_id == House.id)
    .correlate(House)
    .scalar_subquery()
)
_NET_YIELD = (
    select(HouseRentalYield.net_yield)
    .where(HouseRentalYield.house_id == House.id)
    .correlate(House)
    .scalar_subquery()
)
_EXTRAS = (
    _ORIGINAL_PRICE.label("original_price"),
    _GROSS_YIELD.label("gross_yield"),
    _NET_YIELD.label("net_yield"),
)


def _with_extras(rows) -> list[HouseResponse]:
    out = []
    for house, original_price, gross, net in rows:
        response = HouseResponse.model_validate(house)
        response.original_price = original_price
        response.gross_yield_pct = round(float(gross) * 100, 2) if gross is not None else None
        response.cap_rate_pct = round(float(net) * 100, 2) if net is not None else None
        out.append(response)
    return out


# ============================================================================
# Houses
# ============================================================================


@router.get("/api/v1/houses")
async def list_houses(
    q: Optional[str] = Query(
        default=None, description="Text search: title, neighbourhood, street, postal code"
    ),
    city: Optional[str] = Query(default=None, description="Filter by city (case-insensitive)"),
    region: Optional[str] = Query(default=None, description="Filter by district / borough"),
    street: Optional[str] = Query(default=None, description="Filter by street"),
    community: Optional[str] = Query(default=None, description="Filter by neighbourhood"),
    property_type: Optional[str] = Query(
        default=None, description="Comma-separated: condo,townhouse,semi,detached"
    ),
    price_min: Optional[int] = Query(default=None, description="Minimum asking price (CAD)"),
    price_max: Optional[int] = Query(default=None, description="Maximum asking price (CAD)"),
    rooms_min: Optional[int] = Query(default=None, description="Minimum bedrooms"),
    rooms_max: Optional[int] = Query(default=None, description="Maximum bedrooms"),
    baths_min: Optional[float] = Query(default=None, description="Minimum bathrooms"),
    sqft_min: Optional[int] = Query(default=None, description="Minimum interior ft²"),
    sqft_max: Optional[int] = Query(default=None, description="Maximum interior ft²"),
    area_min: Optional[Decimal] = Query(default=None, description="Minimum area (m²)"),
    area_max: Optional[Decimal] = Query(default=None, description="Maximum area (m²)"),
    min_lat: Optional[float] = Query(default=None, description="Map viewport south edge"),
    min_lon: Optional[float] = Query(default=None, description="Map viewport west edge"),
    max_lat: Optional[float] = Query(default=None, description="Map viewport north edge"),
    max_lon: Optional[float] = Query(default=None, description="Map viewport east edge"),
    price_cut: bool = Query(default=False, description="Only listings whose asking price has dropped"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=500, description="Page size"),
    sort: str = Query(
        default="created_at",
        description="Sort field (price, created_at, listed_at, area, sqft, price_per_sqft, gross_yield)",
    ),
    order: str = Query(default="desc", description="Sort order (asc, desc)"),
    db: AsyncSession = Depends(get_db),
) -> HouseListResponse:
    """
    List active listings with filtering and pagination.

    Each item carries price_per_sqft, days_on_market and original_price (first
    recorded asking price) so clients can surface price cuts.
    """
    conditions = [House.is_active == 1]
    if q:
        pattern = f"%{q.strip()}%"
        conditions.append(
            or_(
                House.title.ilike(pattern),
                House.community.ilike(pattern),
                House.street.ilike(pattern),
                House.postal_code.ilike(pattern),
            )
        )
    if city:
        conditions.append(func.lower(House.city) == city.lower())
    if region:
        conditions.append(func.lower(House.region) == region.lower())
    if street:
        conditions.append(House.street.ilike(f"%{street}%"))
    if community:
        conditions.append(House.community.ilike(f"%{community}%"))
    if property_type:
        types = [t.strip().lower() for t in property_type.split(",") if t.strip()]
        conditions.append(House.property_type.in_(types))
    if price_min is not None:
        conditions.append(House.price >= price_min)
    if price_max is not None:
        conditions.append(House.price <= price_max)
    if rooms_min is not None:
        conditions.append(House.rooms >= rooms_min)
    if rooms_max is not None:
        conditions.append(House.rooms <= rooms_max)
    if baths_min is not None:
        conditions.append(House.bathrooms >= baths_min)
    if sqft_min is not None:
        conditions.append(House.sqft >= sqft_min)
    if sqft_max is not None:
        conditions.append(House.sqft <= sqft_max)
    if area_min is not None:
        conditions.append(House.area >= area_min)
    if area_max is not None:
        conditions.append(House.area <= area_max)
    if None not in (min_lat, min_lon, max_lat, max_lon):
        conditions.append(House.latitude.between(min_lat, max_lat))
        conditions.append(House.longitude.between(min_lon, max_lon))
    if price_cut:
        conditions.append(_ORIGINAL_PRICE > House.price)

    # Count total using a dedicated scalar query (not add_columns which produces tuple rows)
    count_result = await db.execute(select(func.count(House.id)).where(*conditions))
    total = count_result.scalar() or 0

    query = select(House, *_EXTRAS).where(*conditions)

    sort_field_map = {
        "price": House.price,
        "created_at": House.created_at,
        "listed_at": House.listed_at,
        "area": House.area,
        "sqft": House.sqft,
        "price_per_sqft": House.price / func.nullif(House.sqft, 0),
        "gross_yield": _GROSS_YIELD,
    }
    sort_field = sort_field_map.get(sort, House.created_at)
    sort_field = sort_field.desc() if order == "desc" else sort_field.asc()
    query = query.order_by(sort_field.nulls_last(), House.id)

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))

    return HouseListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=_with_extras(result.all()),
    )


# Declared before /{house_id} — otherwise "search" is parsed as an int id (422)
@router.get("/api/v1/houses/search")
async def search_houses(
    q: Optional[str] = Query(default=None, description="Full-text search query"),
    city: Optional[str] = Query(default=None, description="Filter by city"),
    region: Optional[str] = Query(default=None, description="Filter by region"),
    db: AsyncSession = Depends(get_db),
):
    """Quick search (typeahead): up to 50 matches by keyword and location."""
    query = select(House, *_EXTRAS).where(House.is_active == 1)

    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                House.title.ilike(pattern),
                House.community.ilike(pattern),
                House.street.ilike(pattern),
                House.postal_code.ilike(pattern),
            )
        )
    if city:
        query = query.where(func.lower(House.city) == city.lower())
    if region:
        query = query.where(func.lower(House.region) == region.lower())

    result = await db.execute(query.order_by(House.id).limit(50))
    return {"items": _with_extras(result.all())}


@router.get("/api/v1/houses/{house_id}")
async def get_house(house_id: int, db: AsyncSession = Depends(get_db)) -> HouseResponse:
    """Get listing details by ID."""
    result = await db.execute(select(House, *_EXTRAS).where(House.id == house_id, House.is_active == 1))
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="House not found")
    return _with_extras([row])[0]


@router.get("/api/v1/houses/{house_id}/price-history")
async def get_price_history(house_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """Asking-price changes over time, oldest first."""
    exists = await db.scalar(select(House.id).where(House.id == house_id))
    if not exists:
        raise HTTPException(status_code=404, detail="House not found")
    result = await db.execute(
        select(HousePriceHistory)
        .where(HousePriceHistory.house_id == house_id)
        .order_by(HousePriceHistory.recorded_at.asc(), HousePriceHistory.id.asc())
    )
    points = [PricePoint.model_validate(p) for p in result.scalars().all()]
    return {"house_id": house_id, "items": points}


_POI_QUERIES = {
    "schools": """
        SELECT s.name, s.level AS detail, l.distance_m, s.latitude, s.longitude
        FROM house_school_links l JOIN house_schools s ON s.id = l.school_id
        WHERE l.house_id = :id ORDER BY l.distance_m
    """,
    "transit": """
        SELECT b.name, b.mode AS detail, l.distance_m, b.latitude, b.longitude
        FROM house_bus_links l JOIN house_bus_stops b ON b.id = l.bus_stop_id
        WHERE l.house_id = :id ORDER BY l.distance_m
    """,
    "hospitals": """
        SELECT h.name, h.hospital_type AS detail, l.distance_m, h.latitude, h.longitude
        FROM house_hospital_links l JOIN house_hospitals h ON h.id = l.hospital_id
        WHERE l.house_id = :id ORDER BY l.distance_m
    """,
}


@router.get("/api/v1/houses/{house_id}/neighbourhood")
async def get_neighbourhood(house_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Nearest schools, transit stops and hospitals (OpenStreetMap, linked by the
    ingestion `osm` loader). Empty lists mean POIs have not been loaded yet.
    """
    exists = await db.scalar(select(House.id).where(House.id == house_id))
    if not exists:
        raise HTTPException(status_code=404, detail="House not found")

    out: dict = {"house_id": house_id, "attribution": "© OpenStreetMap contributors (ODbL)"}
    for key, sql in _POI_QUERIES.items():
        rows = (await db.execute(text(sql), {"id": house_id})).mappings().all()
        out[key] = [
            {
                "name": r["name"],
                "detail": r["detail"],
                "distance_m": r["distance_m"],
                "latitude": float(r["latitude"]) if r["latitude"] is not None else None,
                "longitude": float(r["longitude"]) if r["longitude"] is not None else None,
            }
            for r in rows
        ]
    out["loaded"] = any(out[k] for k in _POI_QUERIES)
    return out


@router.post("/api/v1/houses", dependencies=[Depends(admin_user)])
async def create_house(
    house: HouseCreate,
    db: AsyncSession = Depends(get_db),
) -> HouseResponse:
    """Create a listing (admin only)."""
    data = house.model_dump()
    data["is_synthetic"] = int(data["is_synthetic"])
    new_house = House(**data)
    db.add(new_house)
    await db.commit()
    await db.refresh(new_house)
    db.add(HousePriceHistory(house_id=new_house.id, price=new_house.price))
    await db.commit()
    return HouseResponse.model_validate(new_house)


@router.put("/api/v1/houses/{house_id}", dependencies=[Depends(admin_user)])
async def update_house(
    house_id: int,
    house_update: HouseUpdate,
    db: AsyncSession = Depends(get_db),
) -> HouseResponse:
    """Partially update a listing (admin only). Price changes are recorded in price history."""
    result = await db.execute(select(House).where(House.id == house_id, House.is_active == 1))
    house = result.scalar_one_or_none()
    if not house:
        raise HTTPException(status_code=404, detail="House not found")

    changes = house_update.model_dump(exclude_unset=True)
    if "price" in changes and changes["price"] != house.price:
        db.add(HousePriceHistory(house_id=house.id, price=changes["price"]))
    for key, value in changes.items():
        setattr(house, key, value)

    house.updated_at = datetime.now()
    await db.commit()
    await db.refresh(house)
    return HouseResponse.model_validate(house)


@router.delete("/api/v1/houses/{house_id}", dependencies=[Depends(admin_user)])
async def delete_house(
    house_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Soft-delete a listing (admin only)."""
    result = await db.execute(select(House).where(House.id == house_id, House.is_active == 1))
    house = result.scalar_one_or_none()
    if not house:
        raise HTTPException(status_code=404, detail="House not found")

    house.is_active = 0
    house.updated_at = datetime.now()
    await db.commit()
    return {"status": "ok", "message": "House deactivated"}


# ============================================================================
# Communities
# ============================================================================


@router.get("/api/v1/communities")
async def list_communities(
    city: Optional[str] = Query(default=None, description="Filter by city"),
    region: Optional[str] = Query(default=None, description="Filter by region"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List neighbourhoods with aggregated statistics."""
    query = select(Community).where(Community.house_count > 0)

    if city:
        query = query.where(func.lower(Community.city) == city.lower())
    if region:
        query = query.where(func.lower(Community.region) == region.lower())

    result = await db.execute(query.order_by(Community.city, Community.name))
    communities = result.scalars().all()

    return {"items": [CommunityResponse.model_validate(c) for c in communities]}


@router.get("/api/v1/communities/{community_id}/stats")
async def get_community_stats(
    community_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get aggregated statistics for a neighbourhood."""
    result = await db.execute(select(Community).where(Community.id == community_id))
    community = result.scalar_one_or_none()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")

    house_query = select(
        func.count(House.id),
        func.avg(House.price),
        func.min(House.price),
        func.max(House.price),
        func.avg(House.area),
        func.percentile_cont(0.5).within_group(House.price / func.nullif(House.sqft, 0)),
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
        "median_price_per_sqft": float(house_stats[5]) if house_stats[5] else None,
    }
