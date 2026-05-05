"""
Celery batch tasks for AI insights computation (Phase 5D).

Task execution order per batch:
  1. Fetch houses from DB by IDs
  2. Load ML model (skip price prediction if not trained yet)
  3. For each house: predict price + compute rental yield
  4. Store results in house_price_predictions + house_rental_yields
  5. Trigger city-level narrative generation (one per city, not per house)

The `compute_insights` task name must match exactly what the scraper dispatches:
  "ai_insights.tasks.compute_insights"
"""
import logging
import os
from datetime import datetime, timezone, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from tasks.celery_app import app
from app.feature_engineering import extract_features, features_to_array
from app.ml_models import load_model, compute_rental_yield, predict_price, MODEL_VERSION
from app.narrative import get_adapter

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "SCRAPER_DATABASE_URL",
    "postgresql://root:root@localhost:5432/house_discovery",
)

MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/price_prediction.joblib")


def _get_session() -> Session:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return sessionmaker(bind=engine)()


# ---------------------------------------------------------------------------
# compute_insights — triggered by scraper after each batch insert
# ---------------------------------------------------------------------------

@app.task(name="ai_insights.tasks.compute_insights", bind=True, max_retries=3)
def compute_insights(self, house_ids: list[int], session: Session | None = None):
    """
    Compute price predictions and rental yields for the given house IDs.

    Args:
        house_ids: List of house_houses.id values to process.
        session  : Optional SQLAlchemy Session (injected in tests).

    Retries up to 3 times with exponential backoff on DB/model failures.
    """
    own_session = session is None
    session = session or _get_session()
    pipeline = load_model(MODEL_PATH)

    cities_processed: set[str] = set()

    try:
        for house_id in house_ids:
            house = _fetch_house(session, house_id)
            if house is None:
                logger.warning("House id=%d not found — skipping.", house_id)
                continue

            # Price prediction (skipped if no model trained yet)
            if pipeline is not None:
                try:
                    features = extract_features(house)
                    vec = features_to_array(features)
                    prediction = predict_price(pipeline, vec)
                    _upsert_prediction(session, house_id, prediction)
                except Exception:
                    logger.exception("Price prediction failed for house_id=%d", house_id)

            # Rental yield (always computable)
            try:
                yield_data = compute_rental_yield(
                    house_id=house_id,
                    area=float(house.get("area") or 0),
                    purchase_price=int(house.get("price") or 0),
                    city=house.get("city") or "",
                )
                _upsert_rental_yield(session, yield_data)
            except Exception:
                logger.exception("Rental yield failed for house_id=%d", house_id)

            city = (house.get("city") or "").lower()
            if city:
                cities_processed.add(city)

        session.commit()
        logger.info(
            "compute_insights: processed %d houses across cities: %s",
            len(house_ids),
            cities_processed,
        )

        # Trigger narrative generation for each affected city
        for city in cities_processed:
            generate_daily_narratives.apply_async(
                kwargs={"cities": [city]},
                queue="narratives",
            )

    except Exception as exc:
        session.rollback()
        logger.exception("compute_insights failed: %s", exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)
    finally:
        if own_session:
            session.close()


# ---------------------------------------------------------------------------
# generate_daily_narratives — triggered by Celery Beat (nightly) or after batch
# ---------------------------------------------------------------------------

@app.task(name="ai_insights.tasks.generate_daily_narratives", bind=True, max_retries=3)
def generate_daily_narratives(
    self,
    cities: list[str],
    session: Session | None = None,
    narrative_adapter=None,
):
    """
    Generate city-level market narrative text for each city.
    Calls the narrative adapter once per city (local stub in dev, Azure in prod).

    Args:
        cities           : List of city names to process.
        session          : Optional SQLAlchemy Session (injected in tests).
        narrative_adapter: Optional adapter override (injected in tests).
    """
    own_session = session is None
    session = session or _get_session()
    adapter = narrative_adapter or get_adapter()

    try:
        for city in cities:
            stats = _aggregate_city_stats(session, city)
            try:
                summary = adapter.generate(city=city, stats=stats)
            except Exception:
                logger.exception("Narrative generation failed for city=%s", city)
                continue

            _upsert_market_insight(session, city=city, summary=summary)

        session.commit()
        logger.info("generate_daily_narratives: completed for %s", cities)

    except Exception as exc:
        session.rollback()
        logger.exception("generate_daily_narratives failed: %s", exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)
    finally:
        if own_session:
            session.close()


# ---------------------------------------------------------------------------
# retrain_model — triggered by Celery Beat (weekly)
# ---------------------------------------------------------------------------

@app.task(name="ai_insights.tasks.retrain_model", bind=True, max_retries=2)
def retrain_model(self, session: Session | None = None):
    """
    Retrain the XGBoost model from all historical house data.
    Requires at least 100 houses; logs a warning and exits if fewer.
    """
    from app.feature_engineering import build_training_matrix
    from app.ml_models import train_model, save_model

    own_session = session is None
    session = session or _get_session()

    try:
        houses = _fetch_all_houses(session)
        logger.info("retrain_model: fetched %d houses for training.", len(houses))

        if len(houses) < 100:
            logger.warning(
                "retrain_model: only %d houses available; skipping retrain "
                "(minimum 100 required, 1000+ recommended).",
                len(houses),
            )
            return

        X, y = build_training_matrix(houses)
        if len(X) < 100:
            logger.warning("retrain_model: fewer than 100 valid training rows after filtering.")
            return

        pipeline = train_model(X, y)
        save_model(pipeline, MODEL_PATH)
        logger.info("retrain_model: model saved successfully.")

    except Exception as exc:
        logger.exception("retrain_model failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)
    finally:
        if own_session:
            session.close()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _fetch_house(session: Session, house_id: int) -> dict | None:
    row = session.execute(
        text("SELECT id, city, region, price, area, rooms, floor, age, decoration "
             "FROM house_houses WHERE id = :id"),
        {"id": house_id},
    ).fetchone()
    if row is None:
        return None
    return dict(row._mapping)


def _fetch_all_houses(session: Session) -> list[dict]:
    rows = session.execute(
        text("SELECT id, city, region, price, area, rooms, floor, age, decoration "
             "FROM house_houses WHERE is_active = 1 AND price > 0 AND area > 0")
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def _upsert_prediction(session: Session, house_id: int, prediction: dict) -> None:
    session.execute(
        text("""
            INSERT INTO house_price_predictions
                (house_id, predicted_price, price_low, price_high, confidence, model_version, predicted_at)
            VALUES
                (:house_id, :predicted_price, :price_low, :price_high, :confidence, :model_version, :now)
        """),
        {
            "house_id": house_id,
            "predicted_price": prediction["predicted_price"],
            "price_low": prediction["price_low"],
            "price_high": prediction["price_high"],
            "confidence": prediction["confidence"],
            "model_version": prediction.get("model_version", MODEL_VERSION),
            "now": datetime.now(timezone.utc),
        },
    )


def _upsert_rental_yield(session: Session, yield_data: dict) -> None:
    session.execute(
        text("""
            INSERT INTO house_rental_yields
                (house_id, annual_rent, gross_yield, net_yield, computed_at)
            VALUES
                (:house_id, :annual_rent, :gross_yield, :net_yield, :now)
            ON CONFLICT (house_id) DO UPDATE SET
                annual_rent  = EXCLUDED.annual_rent,
                gross_yield  = EXCLUDED.gross_yield,
                net_yield    = EXCLUDED.net_yield,
                computed_at  = EXCLUDED.computed_at
        """),
        {
            "house_id": yield_data["house_id"],
            "annual_rent": yield_data["annual_rent"],
            "gross_yield": yield_data["gross_yield"],
            "net_yield": yield_data["net_yield"],
            "now": datetime.now(timezone.utc),
        },
    )


def _upsert_market_insight(session: Session, city: str, summary: str, region: str = "") -> None:
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    session.execute(
        text("""
            INSERT INTO house_market_insights
                (city, region, summary_text, model_version, computed_at, expires_at)
            VALUES
                (:city, :region, :summary_text, :model_version, :now, :expires_at)
        """),
        {
            "city": city,
            "region": region or None,
            "summary_text": summary,
            "model_version": "narrative-local-v1",
            "now": datetime.now(timezone.utc),
            "expires_at": expires,
        },
    )


def _aggregate_city_stats(session: Session, city: str) -> dict:
    """Compute city-level stats to feed into the narrative prompt."""
    row = session.execute(
        text("""
            SELECT
                COUNT(h.id)                                         AS listing_count,
                AVG(ry.gross_yield)                                 AS avg_gross_yield,
                AVG(h.price::numeric / NULLIF(h.area, 0))           AS avg_price_per_sqm
            FROM house_houses h
            LEFT JOIN house_rental_yields ry ON ry.house_id = h.id
            WHERE LOWER(h.city) = LOWER(:city) AND h.is_active = 1
        """),
        {"city": city},
    ).fetchone()

    if row is None:
        return {"city": city, "listing_count": 0}

    avg_yield = float(row.avg_gross_yield or 0) * 100   # as percentage
    return {
        "city": city,
        "listing_count": int(row.listing_count or 0),
        "avg_gross_yield_pct": round(avg_yield, 2),
        "price_trend_pct": 0.0,   # placeholder — requires time-series data
        "trend_direction": "stable",
        "top_region": city,
        "top_neighborhoods": f"top areas in {city}",
    }
