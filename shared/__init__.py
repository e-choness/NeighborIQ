"""
Code used by more than one deployable (the API and the two workers):

- shared.models     SQLAlchemy models for every application table
- shared.database   async (API) and sync (workers) sessions
- shared.analytics  fair value from comparables and the cash-flow calculator

Code used by a single service lives in that service. The schema itself is
owned by Alembic (migrations/).
"""

from shared.database.postgres import AsyncSessionLocal, Base, dispose_db, get_db, init_db
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
    RentBenchmark,
    SavedHouse,
    School,
    User,
)

__all__ = [
    "AsyncSessionLocal",
    "Base",
    "BusStop",
    "Community",
    "Hospital",
    "House",
    "HouseBusLink",
    "HouseHospitalLink",
    "HousePriceHistory",
    "HousePricePrediction",
    "HouseRentalYield",
    "HouseSchoolLink",
    "JWTKeyPair",
    "MarketInsight",
    "RefreshToken",
    "RentBenchmark",
    "SavedHouse",
    "School",
    "User",
    "dispose_db",
    "get_db",
    "init_db",
]
