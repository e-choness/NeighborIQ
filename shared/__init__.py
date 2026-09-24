"""
Shared utilities and models for all services.

This is a modular monolith shared layer:
- All services use the same PostgreSQL database
- Domain separation via table prefixes (auth_, house_, etc.)
- Shared Pydantic schemas, SQLAlchemy models, and utility functions
"""

from shared.database.postgres import (
    AsyncSessionLocal,
    Base,
    dispose_db,
    get_db,
    init_db,
)
from shared.models import (
    BusStop,
    Community,
    Hospital,
    House,
    HouseBusLink,
    HouseHospitalLink,
    HousePriceHistory,
    HousePricePrediction,
    HouseRentalYield,
    HouseSchoolLink,
    JWTKeyPair,
    MarketInsight,
    RefreshToken,
    SavedHouse,
    School,
    User,
)
from shared.models.schemas import (
    CommunityBase,
    CommunityResponse,
    HouseBase,
    HouseCreate,
    HouseInsights,
    HouseListResponse,
    HouseResponse,
    PricePrediction,
    RentalYield,
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
)
from shared.utils.jwt_utils import (
    create_access_token,
    create_refresh_token,
    generate_rsa_keypair,
    get_jwks_from_public_key,
    get_key_id,
    hash_token,
    verify_token,
)
from shared.utils.password_utils import hash_password, verify_password

__all__ = [
    # Database
    "Base",
    "AsyncSessionLocal",
    "get_db",
    "init_db",
    "dispose_db",
    # Pydantic schemas
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "HouseBase",
    "HouseCreate",
    "HouseResponse",
    "CommunityBase",
    "CommunityResponse",
    "HouseListResponse",
    "PricePrediction",
    "RentalYield",
    "HouseInsights",
    # Auth ORM models
    "User",
    "JWTKeyPair",
    "RefreshToken",
    # House ORM models
    "House",
    "HousePriceHistory",
    "Community",
    "School",
    "Hospital",
    "BusStop",
    "HouseSchoolLink",
    "HouseHospitalLink",
    "HouseBusLink",
    "SavedHouse",
    # AI ORM models
    "HousePricePrediction",
    "HouseRentalYield",
    "MarketInsight",
    # JWT
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "generate_rsa_keypair",
    "get_key_id",
    "get_jwks_from_public_key",
    "hash_token",
    # Password
    "hash_password",
    "verify_password",
]
