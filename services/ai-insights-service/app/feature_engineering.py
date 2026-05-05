"""
Feature engineering for XGBoost price prediction (Phase 5A).

Extracts numeric features from house data dicts. All features are numeric;
categorical fields (decoration, city, region) are label-encoded against known
lookup tables with a safe fallback for unseen values.
"""
import numpy as np

# Decoration quality ordinal encoding
DECORATION_MAP: dict[str, int] = {
    "original": 0,
    "standard": 1,
    "renovated": 2,
    "luxury": 3,
    # Legacy values kept for backward-compatibility with old scraped data
    "毛坯": 0,
    "简装": 1,
    "精装": 2,
    "豪装": 3,
}
DECORATION_FALLBACK = 1  # "standard"

# Canonical feature order — must match training column order
FEATURE_NAMES = [
    "area",
    "rooms",
    "floor",
    "age",
    "decoration",
    "price_per_sqm_regional",
]


def extract_features(house: dict, regional_price_per_sqm: float = 0.0) -> dict[str, float]:
    """
    Extract numeric features from a house dict.

    Args:
        house: Dict with keys matching HouseItem / house_houses columns.
        regional_price_per_sqm: Regional average price per m² (from DB aggregate).
                                 Pass 0 if unknown; the model tolerates it.

    Returns:
        Flat dict of {feature_name: float} in FEATURE_NAMES order.
    """
    return {
        "area": float(house.get("area") or 0.0),
        "rooms": float(house.get("rooms") or 0),
        "floor": float(house.get("floor") or 1),
        "age": float(house.get("age") or 10),
        "decoration": float(_encode_decoration(house.get("decoration"))),
        "price_per_sqm_regional": float(regional_price_per_sqm),
    }


def features_to_array(features: dict[str, float]) -> np.ndarray:
    """Return a 1-D numpy array in canonical FEATURE_NAMES order."""
    return np.array([features[name] for name in FEATURE_NAMES], dtype=np.float32)


def build_training_matrix(
    houses: list[dict],
    regional_prices: dict[str, float] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build (X, y) training matrices from a list of house dicts.

    Drops houses where price <= 0 or area <= 0 (unusable for regression).

    Args:
        houses: List of house dicts (must include "price" and "area").
        regional_prices: Optional dict {city: avg_price_per_sqm}.

    Returns:
        (X, y) where X.shape == (n_valid, len(FEATURE_NAMES)), y.shape == (n_valid,)
    """
    regional_prices = regional_prices or {}
    X_rows, y_vals = [], []

    for h in houses:
        price = int(h.get("price") or 0)
        area = float(h.get("area") or 0.0)
        if price <= 0 or area <= 0:
            continue
        city = (h.get("city") or "").lower()
        regional_sqm = regional_prices.get(city, 0.0)
        features = extract_features(h, regional_sqm)
        X_rows.append(features_to_array(features))
        y_vals.append(float(price))

    if not X_rows:
        return np.empty((0, len(FEATURE_NAMES)), dtype=np.float32), np.empty((0,), dtype=np.float32)

    return np.vstack(X_rows).astype(np.float32), np.array(y_vals, dtype=np.float32)


def _encode_decoration(decoration: str | None) -> int:
    if decoration is None:
        return DECORATION_FALLBACK
    return DECORATION_MAP.get(str(decoration).strip().lower(), DECORATION_FALLBACK)
