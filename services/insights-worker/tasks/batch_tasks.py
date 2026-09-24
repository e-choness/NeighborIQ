"""
Celery batch tasks for AI insights computation (Phase 5D).

Task execution order per batch:
  1. Fetch houses from DB by IDs
  2. Load ML model (skip price prediction if none has been trained and backtested)
  3. For each house: predict price + estimate rent and unlevered yield
  4. Store results in house_price_predictions + house_rental_yields
  5. Trigger city-level narrative generation (one per city, not per house)

Rental yield uses the city/bedroom rent benchmark and the same cash-flow engine
the UI calls (app/cashflow.py) with no financing: gross = rent×12 / price,
net = NOI / price (cap rate), after vacancy, tax, condo fee, insurance and
maintenance.

The `compute_insights` task name must match exactly what the scraper dispatches:
  "ai_insights.tasks.compute_insights"
"""
import logging
import os
from datetime import datetime, timezone, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from tasks.celery_app import app
from insights.feature_engineering import extract_features, features_to_array
from insights.ml_models import load_model, predict_price, MODEL_VERSION
from insights.narrative import get_adapter
from shared.analytics import cashflow
from shared.database.sync import sync_database_url

logger = logging.getLogger(__name__)

DATABASE_URL = sync_database_url()

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
    bundle = load_model(MODEL_PATH)

    cities_processed: set[str] = set()

    try:
        for house_id in house_ids:
            house = _fetch_house(session, house_id)
            if house is None:
                logger.warning("House id=%d not found — skipping.", house_id)
                continue

            # Price prediction (skipped if no backtested model exists yet)
            if bundle is not None:
                try:
                    vec = features_to_array(extract_features(house, bundle["city_medians"]))
                    prediction = predict_price(bundle, vec)
                    _upsert_prediction(session, house_id, prediction)
                except Exception:
                    logger.exception("Price prediction failed for house_id=%d", house_id)

            # Rental yield (needs a rent benchmark for the city)
            try:
                yield_data = compute_rental_yield(session, house)
                if yield_data is not None:
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

@app.task(name="ai_insights.tasks.recompute_all")
def recompute_all(session: Session | None = None, batch_size: int = 500):
    """Queue compute_insights for every active listing (admin "recompute" button)."""
    own_session = session is None
    session = session or _get_session()
    try:
        ids = session.execute(text("SELECT id FROM house_houses WHERE is_active = 1 ORDER BY id")).scalars().all()
    finally:
        if own_session:
            session.close()
    for i in range(0, len(ids), batch_size):
        compute_insights.apply_async(kwargs={"house_ids": list(ids[i:i + batch_size])}, queue="insights")
    return len(ids)


@app.task(name="ai_insights.tasks.retrain_model", bind=True, max_retries=2)
def retrain_model(self, session: Session | None = None):
    """
    Backtest, then retrain the XGBoost model on all active listings.
    Requires MIN_TRAINING_ROWS listings; logs a warning and exits if fewer.
    """
    from insights.feature_engineering import build_training_matrix
    from insights.ml_models import MIN_TRAINING_ROWS, backtest, save_model, train_model

    own_session = session is None
    session = session or _get_session()

    try:
        houses = _fetch_all_houses(session)
        X, y, medians = build_training_matrix(houses)
        logger.info("retrain_model: %d usable listings.", len(X))
        if len(X) < MIN_TRAINING_ROWS:
            logger.warning(
                "retrain_model: only %d usable listings; skipping (minimum %d).",
                len(X), MIN_TRAINING_ROWS,
            )
            return None

        metrics = backtest(X, y)
        save_model(train_model(X, y), metrics, medians, MODEL_PATH)
        return metrics

    except Exception as exc:
        logger.exception("retrain_model failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)
    finally:
        if own_session:
            session.close()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_HOUSE_COLUMNS = (
    "id, city, region, price, sqft, area, rooms, bathrooms, age, decoration, "
    "property_type, condo_fee, property_tax, latitude, longitude"
)


def _fetch_house(session: Session, house_id: int) -> dict | None:
    row = session.execute(
        text(f"SELECT {_HOUSE_COLUMNS} FROM house_houses WHERE id = :id"),
        {"id": house_id},
    ).fetchone()
    if row is None:
        return None
    return dict(row._mapping)


def _fetch_all_houses(session: Session) -> list[dict]:
    rows = session.execute(
        text(f"SELECT {_HOUSE_COLUMNS} FROM house_houses "
             "WHERE is_active = 1 AND price > 0 AND sqft > 0")
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def compute_rental_yield(session: Session, house: dict) -> dict | None:
    """Unlevered yield from the rent benchmark; None when no benchmark covers the city."""
    beds = min(max(house.get("rooms") or 0, 0), 3)
    rent = session.execute(
        text("SELECT avg_rent FROM house_rent_benchmarks "
             "WHERE LOWER(city) = LOWER(:city) AND bedrooms = :beds"),
        {"city": house.get("city") or "", "beds": beds},
    ).scalar()
    price = int(house.get("price") or 0)
    if not rent or price <= 0:
        return None
    ptype = house.get("property_type")
    result = cashflow.compute(cashflow.CashFlowInput(
        price=price,
        monthly_rent=rent,
        city=house.get("city") or "",
        down_payment_pct=100,  # unlevered: yield is a property metric, not a financing one
        property_tax_annual=house.get("property_tax") or 0,
        condo_fee_monthly=house.get("condo_fee") or 0,
        insurance_monthly=cashflow.default_insurance_monthly(ptype),
        maintenance_pct=cashflow.default_maintenance_pct(ptype, house.get("age")),
    ))
    return {
        "house_id": house["id"],
        "annual_rent": int(rent * 12),
        "gross_yield": round(result.gross_yield_pct / 100, 4),
        "net_yield": round(result.cap_rate_pct / 100, 4),
    }


def _upsert_prediction(session: Session, house_id: int, prediction: dict) -> None:
    session.execute(
        text("""
            INSERT INTO house_price_predictions
                (house_id, predicted_price, price_low, price_high, confidence, model_version, predicted_at)
            VALUES
                (:house_id, :predicted_price, :price_low, :price_high, :confidence, :model_version, :now)
            ON CONFLICT (house_id, model_version) DO UPDATE SET
                predicted_price = EXCLUDED.predicted_price,
                price_low       = EXCLUDED.price_low,
                price_high      = EXCLUDED.price_high,
                confidence      = EXCLUDED.confidence,
                predicted_at    = EXCLUDED.predicted_at
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
            "model_version": f"narrative-{os.getenv('NARRATIVE_PROVIDER', 'local')}-v2",
            "now": datetime.now(timezone.utc),
            "expires_at": expires,
        },
    )


def _aggregate_city_stats(session: Session, city: str) -> dict:
    """
    City-level statistics for the narrative — every value is computed from data.
    A price trend is deliberately omitted: a fair trend needs sold prices or a
    repeat-listing index, and a naive average of asking prices mostly measures
    which homes happen to be listed.
    """
    row = session.execute(
        text("""
            WITH active AS (
                SELECT h.*,
                       (SELECT p.price FROM house_price_history p
                        WHERE p.house_id = h.id ORDER BY p.recorded_at, p.id LIMIT 1) AS first_price
                FROM house_houses h
                WHERE LOWER(h.city) = LOWER(:city) AND h.is_active = 1
            )
            SELECT
                COUNT(*)                                                         AS listing_count,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price)               AS median_price,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price::numeric / NULLIF(sqft, 0))
                                                                                 AS median_ppsf,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(DAY FROM NOW() - listed_at))
                                                                                 AS median_dom,
                AVG(CASE WHEN first_price > price THEN 1.0 ELSE 0.0 END) * 100   AS price_cut_share,
                (SELECT AVG(ry.gross_yield) FROM house_rental_yields ry
                 WHERE ry.house_id IN (SELECT id FROM active))                   AS avg_gross_yield
            FROM active
        """),
        {"city": city},
    ).fetchone()

    if row is None or not row.listing_count:
        return {"city": city, "listing_count": 0}

    top = session.execute(
        text("""
            SELECT h.community, AVG(ry.gross_yield) AS y
            FROM house_houses h JOIN house_rental_yields ry ON ry.house_id = h.id
            WHERE LOWER(h.city) = LOWER(:city) AND h.is_active = 1
            GROUP BY h.community HAVING COUNT(*) >= 5
            ORDER BY y DESC LIMIT 3
        """),
        {"city": city},
    ).fetchall()

    return {
        "city": city,
        "listing_count": int(row.listing_count),
        "median_price": float(row.median_price) if row.median_price else None,
        "median_price_per_sqft": round(float(row.median_ppsf), 2) if row.median_ppsf else None,
        "median_days_on_market": int(row.median_dom) if row.median_dom is not None else None,
        "price_cut_share_pct": round(float(row.price_cut_share), 1) if row.price_cut_share is not None else None,
        "avg_gross_yield_pct": round(float(row.avg_gross_yield) * 100, 2) if row.avg_gross_yield else None,
        "price_trend_pct": None,
        "top_neighborhoods": ", ".join(
            f"{r.community} ({float(r.y) * 100:.1f}%)" for r in top
        ) or None,
    }
