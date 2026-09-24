"""SQLAlchemy models. Table names are prefixed by domain: auth_, house_, portfolio_."""

from shared.models.ai_models import HousePricePrediction, HouseRentalYield, MarketInsight
from shared.models.auth_models import JWTKeyPair, RefreshToken, User
from shared.models.house_models import (
    BusStop,
    Community,
    Hospital,
    House,
    HouseBusLink,
    HouseHospitalLink,
    HousePriceHistory,
    HouseSchoolLink,
    RentBenchmark,
    School,
)
from shared.models.portfolio_models import SavedHouse

__all__ = [
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
]
