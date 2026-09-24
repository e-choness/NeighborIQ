"""
Feature engineering for the XGBoost price model.

All features are numeric. Location enters twice: raw coordinates (the trees
learn neighbourhood effects) and the city's median $/sqft (so one model can
serve cities at very different price levels). The same city medians are
computed at training time and persisted with the model, so inference uses
exactly the values the model was trained with.
"""
import statistics

import numpy as np

# Decoration quality ordinal encoding
DECORATION_MAP: dict[str, int] = {
    "original": 0,
    "standard": 1,
    "renovated": 2,
    "luxury": 3,
}
DECORATION_FALLBACK = 1  # "standard"

PROPERTY_TYPE_MAP: dict[str, int] = {"condo": 0, "townhouse": 1, "semi": 2, "detached": 3}
PROPERTY_TYPE_FALLBACK = 0

# Canonical feature order — must match training column order
FEATURE_NAMES = [
    "sqft",
    "rooms",
    "bathrooms",
    "age",
    "decoration",
    "property_type",
    "latitude",
    "longitude",
    "city_median_ppsf",
]


def city_median_ppsf(houses: list[dict]) -> dict[str, float]:
    """Median asking $/sqft per city (lower-cased), from rows with price and sqft."""
    by_city: dict[str, list[float]] = {}
    for h in houses:
        price, sqft = h.get("price"), h.get("sqft")
        if price and sqft:
            by_city.setdefault((h.get("city") or "").lower(), []).append(price / sqft)
    return {city: statistics.median(v) for city, v in by_city.items()}


def extract_features(house: dict, medians: dict[str, float]) -> dict[str, float]:
    """Flat {feature_name: float} dict in FEATURE_NAMES order. NaN marks missing values."""
    def num(key):
        value = house.get(key)
        return float(value) if value is not None else float("nan")

    city = (house.get("city") or "").lower()
    return {
        "sqft": num("sqft"),
        "rooms": num("rooms"),
        "bathrooms": num("bathrooms"),
        "age": num("age"),
        "decoration": float(_encode(DECORATION_MAP, house.get("decoration"), DECORATION_FALLBACK)),
        "property_type": float(_encode(PROPERTY_TYPE_MAP, house.get("property_type"), PROPERTY_TYPE_FALLBACK)),
        "latitude": num("latitude"),
        "longitude": num("longitude"),
        # XGBoost handles NaN natively — an unseen city is "unknown", not "free"
        "city_median_ppsf": float(medians.get(city, float("nan"))),
    }


def features_to_array(features: dict[str, float]) -> np.ndarray:
    """Return a 1-D numpy array in canonical FEATURE_NAMES order."""
    return np.array([features[name] for name in FEATURE_NAMES], dtype=np.float32)


def build_training_matrix(houses: list[dict]) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """
    Build (X, y, city_medians) from house dicts. Drops rows without a positive
    price or sqft (unusable for regression).
    """
    valid = [h for h in houses if (h.get("price") or 0) > 0 and (h.get("sqft") or 0) > 0]
    medians = city_median_ppsf(valid)
    if not valid:
        empty = np.empty((0, len(FEATURE_NAMES)), dtype=np.float32)
        return empty, np.empty((0,), dtype=np.float32), medians
    X = np.vstack([features_to_array(extract_features(h, medians)) for h in valid])
    y = np.array([float(h["price"]) for h in valid], dtype=np.float32)
    return X.astype(np.float32), y, medians


def _encode(mapping: dict[str, int], value, fallback: int) -> int:
    if value is None:
        return fallback
    return mapping.get(str(value).strip().lower(), fallback)
