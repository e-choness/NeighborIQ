"""Unit tests for ML models (Phase 5B)."""
import numpy as np
import pytest
from app.ml_models import (
    train_model,
    predict_price,
    compute_rental_yield,
    MODEL_VERSION,
    CI_HALF_WIDTH,
    DEFAULT_RENTAL_RATES_PER_SQM_YEAR,
    MANAGEMENT_COST_RATIO,
)


def _make_training_data(n=10):
    rng = np.random.default_rng(42)
    X = rng.random((n, 6)) * 100
    y = rng.random(n) * 1_000_000
    return X, y


class TestTrainModel:
    def test_returns_pipeline(self):
        from sklearn.pipeline import Pipeline
        X, y = _make_training_data(20)
        pipeline = train_model(X, y)
        assert isinstance(pipeline, Pipeline)

    def test_raises_on_empty(self):
        with pytest.raises(ValueError, match="empty"):
            train_model(np.array([]).reshape(0, 6), np.array([]))

    def test_pipeline_can_predict(self):
        X, y = _make_training_data(20)
        pipeline = train_model(X, y)
        preds = pipeline.predict(X[:2])
        assert len(preds) == 2


class TestPredictPrice:
    @pytest.fixture(scope="class")
    def pipeline(self):
        X, y = _make_training_data(20)
        return train_model(X, y)

    def test_returns_dict_with_required_keys(self, pipeline):
        vec = np.array([80.0, 3.0, 5.0, 10.0, 1.0, 5000.0])
        result = predict_price(pipeline, vec)
        assert "predicted_price" in result
        assert "price_low" in result
        assert "price_high" in result
        assert "confidence" in result
        assert "model_version" in result

    def test_confidence_fixed_at_080(self, pipeline):
        vec = np.array([80.0, 3.0, 5.0, 10.0, 1.0, 5000.0])
        result = predict_price(pipeline, vec)
        assert result["confidence"] == 0.80

    def test_model_version_matches(self, pipeline):
        vec = np.array([80.0, 3.0, 5.0, 10.0, 1.0, 5000.0])
        result = predict_price(pipeline, vec)
        assert result["model_version"] == MODEL_VERSION

    def test_ci_bounds(self, pipeline):
        # CI is computed from the raw float prediction before int-casting,
        # so price_low/high may differ from int(predicted_price * factor) by 1.
        # Just verify ordering and approximate width (±15%).
        vec = np.array([80.0, 3.0, 5.0, 10.0, 1.0, 5000.0])
        result = predict_price(pipeline, vec)
        p = result["predicted_price"]
        assert result["price_low"] < p
        assert result["price_high"] > p
        # Width should be close to ±15%
        assert abs(result["price_low"] - p * (1 - CI_HALF_WIDTH)) <= 2
        assert abs(result["price_high"] - p * (1 + CI_HALF_WIDTH)) <= 2

    def test_accepts_1d_vector(self, pipeline):
        vec = np.array([80.0, 3.0, 5.0, 10.0, 1.0, 5000.0])
        result = predict_price(pipeline, vec)
        assert result["predicted_price"] >= 0

    def test_predicted_price_non_negative(self, pipeline):
        # Edge: very unusual input that might produce negative raw prediction
        vec = np.zeros(6)
        result = predict_price(pipeline, vec)
        assert result["predicted_price"] >= 0


class TestComputeRentalYield:
    def test_toronto_rate(self):
        r = compute_rental_yield(house_id=1, area=100.0, purchase_price=500000, city="toronto")
        expected_rent = 100.0 * DEFAULT_RENTAL_RATES_PER_SQM_YEAR["toronto"]
        assert r["annual_rent"] == int(expected_rent)

    def test_gross_yield_formula(self):
        r = compute_rental_yield(house_id=1, area=100.0, purchase_price=500000, city="toronto")
        rate = DEFAULT_RENTAL_RATES_PER_SQM_YEAR["toronto"]
        expected_gross = (100.0 * rate) / 500000
        assert abs(r["gross_yield"] - round(expected_gross, 4)) < 1e-6

    def test_net_yield_accounts_for_management(self):
        r = compute_rental_yield(house_id=1, area=100.0, purchase_price=500000, city="toronto")
        rate = DEFAULT_RENTAL_RATES_PER_SQM_YEAR["toronto"]
        rent = 100.0 * rate
        expected_net = (rent - rent * MANAGEMENT_COST_RATIO) / 500000
        assert abs(r["net_yield"] - round(expected_net, 4)) < 1e-6

    def test_zero_area_returns_zeros(self):
        r = compute_rental_yield(house_id=1, area=0.0, purchase_price=500000, city="toronto")
        assert r["annual_rent"] == 0
        assert r["gross_yield"] == 0.0
        assert r["net_yield"] == 0.0

    def test_zero_price_returns_zeros(self):
        r = compute_rental_yield(house_id=1, area=100.0, purchase_price=0, city="toronto")
        assert r["annual_rent"] == 0

    def test_unknown_city_uses_fallback(self):
        from app.ml_models import FALLBACK_RENTAL_RATE
        r = compute_rental_yield(house_id=1, area=100.0, purchase_price=500000, city="unknown_city")
        assert r["annual_rent"] == int(100.0 * FALLBACK_RENTAL_RATE)

    def test_regional_rate_override(self):
        r = compute_rental_yield(house_id=1, area=100.0, purchase_price=500000, city="toronto", regional_rate=300.0)
        assert r["annual_rent"] == int(100.0 * 300.0)

    def test_house_id_preserved(self):
        r = compute_rental_yield(house_id=42, area=100.0, purchase_price=500000, city="toronto")
        assert r["house_id"] == 42
