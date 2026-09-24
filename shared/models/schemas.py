"""
Pydantic request/response schemas (DTOs).

These are separate from SQLAlchemy ORM models to maintain a clean API contract.
Schemas are used for validation and serialization.
"""

import json
from typing import Optional
from datetime import datetime, timezone
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_serializer,
    model_validator,
)

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

    model_config = ConfigDict(from_attributes=True)


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
    """Shared fields for house objects (Canadian listing model, prices in CAD)."""

    title: str
    community: Optional[str] = None  # Neighbourhood
    city: str
    region: str  # District / borough
    street: Optional[str] = None
    postal_code: Optional[str] = None
    property_type: Optional[str] = None  # condo|townhouse|semi|detached
    price: int  # Asking price, CAD
    sqft: Optional[int] = None
    area: Optional[float] = None  # m², derived from sqft
    rooms: Optional[int] = None  # Bedrooms (0 = bachelor)
    bathrooms: Optional[float] = None
    parking: Optional[int] = None
    floor: Optional[int] = None
    decoration: Optional[str] = None  # original|standard|renovated|luxury
    age: Optional[int] = None  # Years
    condo_fee: Optional[int] = None  # Monthly, CAD
    property_tax: Optional[int] = None  # Annual, CAD
    status: Optional[str] = "active"
    listed_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    url: Optional[str] = None
    images: Optional[list[str]] = None
    source: Optional[str] = None
    is_synthetic: bool = False

    @field_validator("is_synthetic", mode="before")
    @classmethod
    def _flag(cls, v):
        return bool(v)

    @field_validator("images", mode="before")
    @classmethod
    def _parse_images(cls, v):
        # Stored as a JSON string in house_houses.images
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
            except ValueError:
                return [v] if v else []
            return parsed if isinstance(parsed, list) else []
        return v


class HouseCreate(HouseBase):
    """DTO for creating a house (admin only)."""

    pass


class HouseUpdate(BaseModel):
    """Partial update (admin only) — only supplied fields are changed."""

    title: Optional[str] = None
    community: Optional[str] = None
    street: Optional[str] = None
    postal_code: Optional[str] = None
    property_type: Optional[str] = None
    price: Optional[int] = Field(default=None, gt=0)
    sqft: Optional[int] = None
    rooms: Optional[int] = None
    bathrooms: Optional[float] = None
    parking: Optional[int] = None
    condo_fee: Optional[int] = None
    property_tax: Optional[int] = None
    status: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class HouseResponse(HouseBase):
    """DTO for returning house details."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    price_per_sqft: Optional[float] = None
    days_on_market: Optional[int] = None
    original_price: Optional[int] = None  # First recorded asking price
    gross_yield_pct: Optional[float] = None  # Benchmark rent × 12 / price
    cap_rate_pct: Optional[float] = None  # Unlevered NOI / price

    model_config = ConfigDict(from_attributes=True)

    @property
    def price_cut_pct(self) -> Optional[float]:
        if self.original_price and self.original_price > self.price:
            return round((self.original_price - self.price) / self.original_price * 100, 1)
        return None

    @model_serializer(mode="wrap")
    def _serialize(self, handler):
        data = handler(self)
        data["price_cut_pct"] = self.price_cut_pct
        return data

    @model_validator(mode="after")
    def _derive(self):
        if self.sqft and self.price and self.price_per_sqft is None:
            self.price_per_sqft = round(self.price / self.sqft, 2)
        if self.listed_at and self.days_on_market is None:
            listed = self.listed_at if self.listed_at.tzinfo else self.listed_at.replace(tzinfo=timezone.utc)
            self.days_on_market = max(0, (datetime.now(timezone.utc) - listed).days)
        return self


class PricePoint(BaseModel):
    price: int
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    street: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CommunityResponse(CommunityBase):
    """DTO for returning community."""

    id: int
    house_count: int
    avg_price: Optional[float]

    model_config = ConfigDict(from_attributes=True)


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
