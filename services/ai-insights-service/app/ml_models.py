"""
ML models for price prediction and rental yield estimation (Phase 5B).

Price Prediction:
  Algorithm : XGBoost regression wrapped in a scikit-learn Pipeline
  Features  : area, rooms, floor, age, decoration, price_per_sqm_regional
  Output    : predicted_price (point) + 80% CI (±15% heuristic until quantile
              regression is warranted by data volume)
  Persistence: joblib serialisation to MODEL_PATH

Rental Yield:
  Pure formula — no ML needed:
    annual_rent = area × regional_rate_per_sqm_per_year
    gross_yield = annual_rent / purchase_price
    net_yield   = (annual_rent − management_costs) / purchase_price
"""
import logging
import os

import joblib
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

logger = logging.getLogger(__name__)

MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/price_prediction.joblib")
MODEL_VERSION = "v1.0.0-xgboost"

# CI half-width: 80% CI approximated as ±15% of the point estimate.
# Replace with quantile regression (XGBRegressor objective="reg:quantileerror")
# once sufficient data has accumulated (1 000+ houses).
CI_HALF_WIDTH = 0.15

# ---------------------------------------------------------------------------
# Regional rental rates (CAD per m² per year) — update from market benchmarks
# ---------------------------------------------------------------------------
DEFAULT_RENTAL_RATES_PER_SQM_YEAR: dict[str, float] = {
    "toronto": 350.0,
    "vancouver": 400.0,
    "calgary": 220.0,
    "ottawa": 240.0,
    "montreal": 200.0,
    "edmonton": 190.0,
    "winnipeg": 170.0,
}
FALLBACK_RENTAL_RATE = 250.0
MANAGEMENT_COST_RATIO = 0.10   # 10% of annual rent


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------

def train_model(X: np.ndarray, y: np.ndarray) -> Pipeline:
    """
    Train an XGBoost regression pipeline on (X, y).

    Minimum recommended training set: 1 000 rows. For smaller sets the model
    still trains but predictions may be unreliable — the API consumer is
    responsible for communicating this via the confidence field.

    Args:
        X: Feature matrix of shape (n_samples, n_features).
        y: Target vector of shape (n_samples,) — house prices.

    Returns:
        Fitted scikit-learn Pipeline (StandardScaler + XGBRegressor).
    """
    if len(X) == 0:
        raise ValueError("Cannot train on an empty dataset.")

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", xgb.XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=0,
            tree_method="hist",   # fast on CPU
        )),
    ])
    pipeline.fit(X, y)
    logger.info("Model trained on %d samples.", len(X))
    return pipeline


def save_model(pipeline: Pipeline, path: str = MODEL_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump({"pipeline": pipeline, "version": MODEL_VERSION}, path)
    logger.info("Model saved to %s", path)


def load_model(path: str = MODEL_PATH) -> Pipeline | None:
    """Return the fitted pipeline, or None if no model file exists yet."""
    if not os.path.exists(path):
        logger.info("No model file at %s — skipping price prediction.", path)
        return None
    payload = joblib.load(path)
    return payload["pipeline"]


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

def predict_price(pipeline: Pipeline, feature_vector: np.ndarray) -> dict:
    """
    Predict house price for a single feature vector.

    Args:
        pipeline: Fitted scikit-learn Pipeline from train_model().
        feature_vector: 1-D numpy array of shape (n_features,).

    Returns:
        Dict with predicted_price, price_low, price_high, confidence, model_version.
    """
    if feature_vector.ndim == 1:
        feature_vector = feature_vector.reshape(1, -1)

    predicted = float(pipeline.predict(feature_vector)[0])
    predicted = max(0.0, predicted)   # prices can't be negative
    low = predicted * (1 - CI_HALF_WIDTH)
    high = predicted * (1 + CI_HALF_WIDTH)

    return {
        "predicted_price": int(predicted),
        "price_low": int(low),
        "price_high": int(high),
        "confidence": 0.80,
        "model_version": MODEL_VERSION,
    }


# ---------------------------------------------------------------------------
# Rental yield formula
# ---------------------------------------------------------------------------

def compute_rental_yield(
    house_id: int,
    area: float,
    purchase_price: int,
    city: str,
    regional_rate: float | None = None,
) -> dict:
    """
    Compute formula-based rental yield for a house.

    annual_rent = area (m²) × rate (CAD/m²/year)
    gross_yield = annual_rent / purchase_price
    net_yield   = (annual_rent − management_costs) / purchase_price

    Args:
        house_id       : DB primary key.
        area           : Floor area in m².
        purchase_price : Listing price.
        city           : City name (used to look up regional rate).
        regional_rate  : Override rate in CAD/m²/year; uses city default if None.

    Returns:
        Dict with house_id, annual_rent, gross_yield, net_yield.
    """
    if area <= 0 or purchase_price <= 0:
        return {
            "house_id": house_id,
            "annual_rent": 0,
            "gross_yield": 0.0,
            "net_yield": 0.0,
        }

    rate = regional_rate if regional_rate is not None else (
        DEFAULT_RENTAL_RATES_PER_SQM_YEAR.get(city.lower(), FALLBACK_RENTAL_RATE)
    )
    annual_rent = area * rate
    management_costs = annual_rent * MANAGEMENT_COST_RATIO
    gross_yield = annual_rent / purchase_price
    net_yield = (annual_rent - management_costs) / purchase_price

    return {
        "house_id": house_id,
        "annual_rent": int(annual_rent),
        "gross_yield": round(gross_yield, 4),
        "net_yield": round(net_yield, 4),
    }
