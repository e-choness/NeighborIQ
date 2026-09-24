"""Unit tests for features and the backtested price model."""
import math

import numpy as np
import pytest

from app.feature_engineering import (
    FEATURE_NAMES,
    build_training_matrix,
    city_median_ppsf,
    extract_features,
)
from app.ml_models import backtest, load_model, predict_price, save_model, train_model


def _houses(n=300, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        city, base = ("Toronto", 1000) if i % 2 else ("Calgary", 450)
        sqft = int(rng.uniform(500, 2500))
        out.append({
            "city": city, "sqft": sqft, "rooms": int(rng.integers(1, 5)), "bathrooms": 2,
            "age": int(rng.integers(1, 60)), "decoration": "standard",
            "property_type": "condo" if sqft < 1200 else "detached",
            "latitude": 43.6 + rng.normal(0, 0.02), "longitude": -79.4 + rng.normal(0, 0.02),
            "price": int(sqft * base * rng.lognormal(0, 0.08)),
        })
    return out


def test_city_medians_are_per_city():
    medians = city_median_ppsf(_houses())
    assert medians["toronto"] > 2 * medians["calgary"]


def test_feature_vector_order_and_missing_values():
    f = extract_features({"city": "Nowhere", "sqft": 800}, {"toronto": 1000})
    assert list(f) == FEATURE_NAMES
    assert f["sqft"] == 800
    assert math.isnan(f["city_median_ppsf"])  # unknown city is unknown, not 0
    assert math.isnan(f["latitude"])


def test_training_matrix_drops_unusable_rows():
    houses = _houses(10) + [{"city": "Toronto", "price": 0, "sqft": 900}, {"city": "Toronto", "price": 1, "sqft": None}]
    X, y, medians = build_training_matrix(houses)
    assert X.shape == (10, len(FEATURE_NAMES)) and y.shape == (10,)


def test_backtest_band_and_round_trip(tmp_path):
    X, y, medians = build_training_matrix(_houses())
    metrics = backtest(X, y)
    assert metrics["n_test"] == 60
    assert metrics["rel_error_low"] < 0 < metrics["rel_error_high"]
    assert 0 < metrics["mape_pct"] < 30

    path = str(tmp_path / "m.joblib")
    save_model(train_model(X, y), metrics, medians, path)
    bundle = load_model(path)
    p = predict_price(bundle, X[0])
    assert p["price_low"] < p["predicted_price"] < p["price_high"]
    assert p["confidence"] == pytest.approx(0.8)


def test_backtest_refuses_tiny_datasets():
    X, y, _ = build_training_matrix(_houses(50))
    with pytest.raises(ValueError):
        backtest(X, y)


def test_legacy_model_without_metrics_is_ignored(tmp_path):
    import joblib
    path = str(tmp_path / "old.joblib")
    joblib.dump({"pipeline": object(), "version": "v1"}, path)
    assert load_model(path) is None
