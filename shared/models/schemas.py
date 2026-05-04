"""
Pydantic request/response schemas (DTOs).

These are separate from SQLAlchemy ORM models to maintain a clean API contract.
Schemas are used for validation and serialization.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# Auth DTOs
# ============================================================================

class UserBase(BaseModel):
    """Shared fields for user objects."""

    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    """DTO for user registration."""

    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    """DTO for user login."""

    email: EmailStr
    password: str


class UserResponse(UserBase):
    """DTO for returning user info (never includes password)."""

    id: int
    role: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """DTO for token endpoints (for API contracts; actual JWT sent via HttpOnly cookie)."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


# ============================================================================
# House DTOs
# ============================================================================

class HouseBase(BaseModel):
    """Shared fields for house objects."""

    title: str
    community: str
    city: str
    region: str
    street: str
    price: int  # In yuan
    area: float  # m²
    rooms: int
    floor: Optional[int] = None
    decoration: Optional[str] = None  # "精装", "简装", etc.
    age: Optional[int] = None  # Years
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    url: Optional[str] = None
    images: Optional[list[str]] = None


class HouseCreate(HouseBase):
    """DTO for creating a house (admin only)."""

    pass


class HouseResponse(HouseBase):
    """DTO for returning house details."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class HouseListResponse(BaseModel):
    """Paginated list response."""

    total: int
    page: int
    page_size: int
    items: list[HouseResponse]


# ============================================================================
# Community DTOs
# ============================================================================

class CommunityBase(BaseModel):
    """Shared fields for community."""

    name: str
    city: str
    region: str
    street: str
    latitude: float
    longitude: float


class CommunityResponse(CommunityBase):
    """DTO for returning community."""

    id: int
    house_count: int
    avg_price: Optional[float]

    class Config:
        from_attributes = True


# ============================================================================
# AI Insights DTOs
# ============================================================================

class PricePrediction(BaseModel):
    """Price prediction with confidence interval."""

    predicted_price: int
    price_low: int
    price_high: int
    confidence: float  # 0.0-1.0
    model_version: str


class RentalYield(BaseModel):
    """Rental yield estimation."""

    annual_rent: int
    gross_yield: float  # percentage
    net_yield: float  # percentage


class HouseInsights(BaseModel):
    """Complete insights for a house."""

    house_id: int
    price_prediction: Optional[PricePrediction] = None
    rental_yield: Optional[RentalYield] = None
    market_score: Optional[float] = None  # 0-100


# ============================================================================
# Error DTOs
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


# ============================================================================
# Health DTOs
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""

    status: str  # "ok" or "degraded"
    service: str
    version: str
    timestamp: datetime
