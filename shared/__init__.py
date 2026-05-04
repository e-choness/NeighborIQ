"""
Shared utilities and models for all services.

This is a modular monolith shared layer:
- All services use the same PostgreSQL database
- Domain separation via table prefixes (auth_, house_, etc.)
- Shared Pydantic schemas, SQLAlchemy models, and utility functions
"""

from shared.database.postgres import (
    Base,
    AsyncSessionLocal,
    get_db,
    init_db,
    dispose_db,
)
from shared.models.schemas import (
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    HouseBase,
    HouseCreate,
    HouseResponse,
    CommunityBase,
    CommunityResponse,
    HouseListResponse,
    PricePrediction,
    RentalYield,
    HouseInsights,
)
from shared.models import (
    User,
    JWTKeyPair,
    RefreshToken,
    House,
    HousePriceHistory,
    Community,
    School,
    Hospital,
    BusStop,
    HouseSchoolLink,
    HouseHospitalLink,
    HouseBusLink,
)
from shared.utils.jwt_utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_rsa_keypair,
    get_key_id,
    get_jwks_from_public_key,
    hash_token,
)
from shared.utils.password_utils import hash_password, verify_password

__all__ = [
    # Database
    "Base",
    "AsyncSessionLocal",
    "get_db",
    "init_db",
    "dispose_db",
    # Schemas
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
    # Models
    "User",
    "JWTKeyPair",
    "RefreshToken",
    "House",
    "HousePriceHistory",
    "Community",
    "School",
    "Hospital",
    "BusStop",
    "HouseSchoolLink",
    "HouseHospitalLink",
    "HouseBusLink",
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
