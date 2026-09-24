"""
XGBoost price model with an honest, backtested error band.

Training holds out 20% of listings, measures the model's relative error on
them, then refits on everything. The 10th/90th percentiles of that held-out
error define the displayed range, so "80%" means "on unseen listings, the
asking price fell inside this band 80% of the time" — an empirical claim we can
check, not a hard-coded ±15%.

The model is off in the UI by default (ML_PREDICTIONS_ENABLED=0): comparable
listings are the primary valuation. Turn it on only once the backtest metrics
(stored with the model) are good enough for your market.
"""
import logging
import os

import joblib
import numpy as np
import xgboost as xgb

logger = logging.getLogger(__name__)

MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/price_prediction.joblib")
MODEL_VERSION = "v2.0.0-xgboost"
MIN_TRAINING_ROWS = 100
HOLDOUT_SHARE = 0.2
INTERVAL_QUANTILES = (0.10, 0.90)


def ml_predictions_enabled() -> bool:
    return os.getenv("ML_PREDICTIONS_ENABLED", "0") == "1"


def _regressor() -> xgb.XGBRegressor:
    # Trees are scale-invariant, so no StandardScaler is needed.
    return xgb.XGBRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
        tree_method="hist",
    )


def train_model(X: np.ndarray, y: np.ndarray) -> xgb.XGBRegressor:
    """Fit on all rows. Raises on empty input."""
    if len(X) == 0:
        raise ValueError("Cannot train on an empty dataset.")
    model = _regressor()
    model.fit(X, y)
    logger.info("Model trained on %d samples.", len(X))
    return model


def backtest(X: np.ndarray, y: np.ndarray, seed: int = 42) -> dict:
    """
    Held-out evaluation. Relative error e = (actual − predicted) / predicted, so
    actual ≈ predicted × (1 + e). Returns MAPE and the e quantiles used for the band.
    """
    if len(X) < MIN_TRAINING_ROWS:
        raise ValueError(f"Need at least {MIN_TRAINING_ROWS} rows to backtest, got {len(X)}.")
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(X))
    n_test = max(1, int(len(X) * HOLDOUT_SHARE))
    test, train = idx[:n_test], idx[n_test:]

    model = train_model(X[train], y[train])
    predicted = np.maximum(model.predict(X[test]), 1.0)
    rel_error = (y[test] - predicted) / predicted
    low_q, high_q = np.quantile(rel_error, INTERVAL_QUANTILES)
    return {
        "n_train": int(len(train)),
        "n_test": int(n_test),
        "mape_pct": round(float(np.mean(np.abs(y[test] - predicted) / y[test]) * 100), 2),
        "rel_error_low": float(low_q),
        "rel_error_high": float(high_q),
        "coverage": INTERVAL_QUANTILES[1] - INTERVAL_QUANTILES[0],
    }


def save_model(model, metrics: dict, city_medians: dict[str, float], path: str = MODEL_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(
        {"model": model, "version": MODEL_VERSION, "metrics": metrics, "city_medians": city_medians},
        path,
    )
    logger.info("Model saved to %s (MAPE %.1f%%)", path, metrics.get("mape_pct", float("nan")))


def load_model(path: str = MODEL_PATH) -> dict | None:
    """
    Return {"model", "version", "metrics", "city_medians"} or None if there is no
    usable model (missing file, or an older payload without backtest metrics).
    """
    if not os.path.exists(path):
        logger.info("No model file at %s — skipping price prediction.", path)
        return None
    payload = joblib.load(path)
    if not isinstance(payload, dict) or "metrics" not in payload:
        logger.warning("Model at %s has no backtest metrics — retrain before use.", path)
        return None
    return payload


def predict_price(bundle: dict, feature_vector: np.ndarray) -> dict:
    """Point prediction plus the backtested band."""
    if feature_vector.ndim == 1:
        feature_vector = feature_vector.reshape(1, -1)
    predicted = max(0.0, float(bundle["model"].predict(feature_vector)[0]))
    metrics = bundle["metrics"]
    return {
        "predicted_price": int(predicted),
        "price_low": int(predicted * (1 + metrics["rel_error_low"])),
        "price_high": int(predicted * (1 + metrics["rel_error_high"])),
        "confidence": round(metrics["coverage"], 4),
        "model_version": bundle.get("version", MODEL_VERSION),
    }
