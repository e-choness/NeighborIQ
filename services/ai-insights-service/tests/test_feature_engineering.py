"""Unit tests for feature engineering (Phase 5A)."""
import numpy as np
import pytest
from app.feature_engineering import (
    extract_features,
    features_to_array,
    build_training_matrix,
    FEATURE_NAMES,
    DECORATION_MAP,
)


def _house(**kwargs):
    base = {
        "id": 1,
        "city": "toronto",
        "region": "downtown",
        "price": 500000,
        "area": 80.0,
        "rooms": 3,
        "floor": 5,
        "age": 10,
        "decoration": "standard",
    }
    base.update(kwargs)
    return base


class TestExtractFeatures:
    def test_basic_extraction(self):
        h = _house()
        f = extract_features(h)
        assert f["area"] == 80.0
        assert f["rooms"] == 3.0
        assert f["floor"] == 5.0
        assert f["age"] == 10.0
        assert f["decoration"] == DECORATION_MAP["standard"]

    def test_decoration_map_standard(self):
        f = extract_features(_house(decoration="standard"))
        assert f["decoration"] == DECORATION_MAP["standard"]

    def test_decoration_map_luxury(self):
        f = extract_features(_house(decoration="luxury"))
        assert f["decoration"] == DECORATION_MAP["luxury"]

    def test_decoration_unknown_defaults_to_fallback(self):
        from app.feature_engineering import DECORATION_FALLBACK
        f = extract_features(_house(decoration="unknown_type"))
        assert f["decoration"] == DECORATION_FALLBACK

    def test_none_area_and_rooms_default_to_zero(self):
        h = _house(area=None, rooms=None)
        f = extract_features(h)
        assert f["area"] == 0.0
        assert f["rooms"] == 0.0

    def test_none_floor_defaults_to_one(self):
        f = extract_features(_house(floor=None))
        assert f["floor"] == 1.0

    def test_none_age_defaults_to_ten(self):
        f = extract_features(_house(age=None))
        assert f["age"] == 10.0

    def test_none_decoration_defaults_to_fallback(self):
        from app.feature_engineering import DECORATION_FALLBACK
        f = extract_features(_house(decoration=None))
        assert f["decoration"] == float(DECORATION_FALLBACK)

    def test_regional_price_per_sqm_passed_through(self):
        f = extract_features(_house(), regional_price_per_sqm=5000.0)
        assert f["price_per_sqm_regional"] == 5000.0

    def test_regional_price_per_sqm_default_zero(self):
        f = extract_features(_house())
        assert f["price_per_sqm_regional"] == 0.0


class TestFeaturesToArray:
    def test_returns_numpy_array(self):
        f = extract_features(_house())
        arr = features_to_array(f)
        assert isinstance(arr, np.ndarray)

    def test_array_length_matches_feature_names(self):
        f = extract_features(_house())
        arr = features_to_array(f)
        assert len(arr) == len(FEATURE_NAMES)

    def test_order_matches_feature_names(self):
        f = extract_features(_house(area=90.0, rooms=2))
        arr = features_to_array(f)
        area_idx = FEATURE_NAMES.index("area")
        rooms_idx = FEATURE_NAMES.index("rooms")
        assert arr[area_idx] == 90.0
        assert arr[rooms_idx] == 2.0


class TestBuildTrainingMatrix:
    def test_basic_matrix(self):
        houses = [_house(price=500000), _house(price=600000, area=100.0)]
        X, y = build_training_matrix(houses)
        assert X.shape[0] == 2
        assert X.shape[1] == len(FEATURE_NAMES)
        assert len(y) == 2

    def test_filters_zero_price(self):
        houses = [_house(price=0), _house(price=500000)]
        X, y = build_training_matrix(houses)
        assert X.shape[0] == 1
        assert y[0] == 500000

    def test_filters_zero_area(self):
        houses = [_house(area=0), _house(area=80.0, price=500000)]
        X, y = build_training_matrix(houses)
        assert X.shape[0] == 1

    def test_empty_input(self):
        X, y = build_training_matrix([])
        assert X.shape[0] == 0
