from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

T = TypeVar("T")


class ApiResponse(BaseModel):
    status: str = "ok"
    message: str | None = None


class UserDTO(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str | None = None
    roles: list[str] = Field(default_factory=list)


class HouseDTO(BaseModel):
    id: UUID
    title: str
    city: str
    region: str | None = None
    street: str | None = None
    community_id: UUID | None = None
    price: Decimal | None = None
    area_sqm: Decimal | None = None
    rooms: int | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    scraped_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CommunityDTO(BaseModel):
    id: UUID
    name: str
    city: str
    region: str | None = None
    street: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
