import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

from app.cashflow import (
    CashFlowInput,
    CashFlowResult,
    compute as compute_cash_flow,
    default_insurance_monthly,
    default_maintenance_pct,
)
from app.ml_models import ml_predictions_enabled
from app.valuation import (
    RentEstimate,
    Valuation,
    fetch_subject,
    rent_estimate_for,
    valuation_for,
)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# ---------------------------------------------------------------------------
# Database (sync SQLAlchemy — Celery tasks and FastAPI share the same engine)
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv(
    "SCRAPER_DATABASE_URL",
    "postgresql://root:root@localhost:5432/house_discovery",
)

_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
_SessionLocal = sessionmaker(bind=_engine)


def get_db():
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class MlPrediction(BaseModel):
    predicted_price: int
    price_low: int
    price_high: int
    coverage: float  # share of held-out listings that fell inside [low, high]
    model_version: str


class CashFlowSummary(BaseModel):
    inputs: CashFlowInput
    result: CashFlowResult


class HouseInsightsResponse(BaseModel):
    house_id: int
    is_synthetic: bool = False
    valuation: Optional[Valuation] = None
    rent: Optional[RentEstimate] = None
    cash_flow: Optional[CashFlowSummary] = None
    ml: Optional[MlPrediction] = None
    # Flat fields kept for the pre-redesign UI: valuation-backed, never fabricated.
    predicted_price: Optional[int] = None
    price_low: Optional[int] = None
    price_high: Optional[int] = None
    confidence: Optional[float] = None
    model_version: Optional[str] = None
    annual_rent: Optional[int] = None
    gross_yield: Optional[float] = None
    net_yield: Optional[float] = None


class NeighborhoodAnalysisResponse(BaseModel):
    city: str
    region: str
    market_summary: Optional[str] = None
    listing_count: int = 0
    avg_gross_yield_pct: Optional[float] = None
    median_price: Optional[int] = None
    median_price_per_sqft: Optional[float] = None
    avg_price_per_sqm: float = 0.0  # legacy field


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="AI Insights Service", version="0.3.0")


def default_cash_flow_inputs(subject: dict, rent: Optional[RentEstimate]) -> CashFlowInput:
    """Investor defaults for a listing — every value is editable in the UI."""
    ptype = subject.get("property_type")
    return CashFlowInput(
        price=subject["price"],
        monthly_rent=rent.monthly_rent if rent else 0,
        city=subject.get("city") or "",
        property_tax_annual=subject.get("property_tax") or 0,
        condo_fee_monthly=subject.get("condo_fee") or 0,
        insurance_monthly=default_insurance_monthly(ptype),
        maintenance_pct=default_maintenance_pct(ptype, subject.get("age")),
    )


def _latest_ml_prediction(db: Session, house_id: int) -> Optional[MlPrediction]:
    if not ml_predictions_enabled():
        return None
    row = db.execute(
        text("""
            SELECT predicted_price, price_low, price_high, confidence, model_version
            FROM house_price_predictions
            WHERE house_id = :house_id
            ORDER BY predicted_at DESC
            LIMIT 1
        """),
        {"house_id": house_id},
    ).fetchone()
    if row is None:
        return None
    return MlPrediction(
        predicted_price=row.predicted_price, price_low=row.price_low, price_high=row.price_high,
        coverage=float(row.confidence), model_version=row.model_version,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/houses/{house_id}/insights", response_model=HouseInsightsResponse)
def get_house_insights(house_id: int, db: Session = Depends(get_db)):
    """
    Everything an investor needs for one listing: comps-based fair value, a rent
    estimate, and a cash-flow projection at default assumptions (recompute with
    POST /api/v1/cashflow after editing them).
    """
    subject = fetch_subject(db, house_id)
    if subject is None:
        raise HTTPException(status_code=404, detail=f"House {house_id} not found")

    valuation = valuation_for(db, subject)
    rent = rent_estimate_for(db, subject["city"], subject.get("rooms"))
    inputs = default_cash_flow_inputs(subject, rent)
    cash_flow = CashFlowSummary(inputs=inputs, result=compute_cash_flow(inputs)) if rent else None
    ml = _latest_ml_prediction(db, house_id)

    return HouseInsightsResponse(
        house_id=house_id,
        is_synthetic=bool(subject.get("is_synthetic")),
        valuation=valuation,
        rent=rent,
        cash_flow=cash_flow,
        ml=ml,
        predicted_price=valuation.fair_value if valuation else None,
        price_low=valuation.fair_value_low if valuation else None,
        price_high=valuation.fair_value_high if valuation else None,
        confidence=None,
        model_version=valuation.method if valuation else None,
        annual_rent=rent.monthly_rent * 12 if rent else None,
        gross_yield=round(cash_flow.result.gross_yield_pct / 100, 4) if cash_flow else None,
        net_yield=round(cash_flow.result.cap_rate_pct / 100, 4) if cash_flow else None,
    )


@app.get("/api/v1/houses/{house_id}/valuation", response_model=Optional[Valuation])
def get_house_valuation(house_id: int, db: Session = Depends(get_db)):
    """Comparable-listing valuation only. null = not enough comparable listings."""
    subject = fetch_subject(db, house_id)
    if subject is None:
        raise HTTPException(status_code=404, detail=f"House {house_id} not found")
    return valuation_for(db, subject)


@app.post("/api/v1/cashflow", response_model=CashFlowResult)
def post_cash_flow(inputs: CashFlowInput):
    """Stateless cash-flow projection for user-edited assumptions."""
    return compute_cash_flow(inputs)


@app.get("/api/v1/neighborhoods/{city}/{region}/analysis", response_model=NeighborhoodAnalysisResponse)
def get_neighborhood_analysis(city: str, region: str, db: Session = Depends(get_db)):
    insight_row = db.execute(
        text("""
            SELECT summary_text
            FROM house_market_insights
            WHERE LOWER(city) = LOWER(:city)
              AND (LOWER(region) = LOWER(:region) OR region IS NULL)
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY computed_at DESC
            LIMIT 1
        """),
        {"city": city, "region": region},
    ).fetchone()

    stats_row = db.execute(
        text("""
            SELECT
                COUNT(h.id)                                                     AS listing_count,
                AVG(ry.gross_yield)                                             AS avg_gross_yield,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY h.price)            AS median_price,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY h.price::numeric / NULLIF(h.sqft, 0))
                                                                                AS median_ppsf,
                AVG(h.price::numeric / NULLIF(h.area, 0))                       AS avg_price_per_sqm
            FROM house_houses h
            LEFT JOIN house_rental_yields ry ON ry.house_id = h.id
            WHERE LOWER(h.city) = LOWER(:city)
              AND LOWER(h.region) = LOWER(:region)
              AND h.is_active = 1
        """),
        {"city": city, "region": region},
    ).fetchone()

    count = int(stats_row.listing_count or 0) if stats_row else 0
    return NeighborhoodAnalysisResponse(
        city=city,
        region=region,
        market_summary=insight_row.summary_text if insight_row else None,
        listing_count=count,
        avg_gross_yield_pct=round(float(stats_row.avg_gross_yield) * 100, 2)
        if count and stats_row.avg_gross_yield else None,
        median_price=int(stats_row.median_price) if count and stats_row.median_price else None,
        median_price_per_sqft=round(float(stats_row.median_ppsf), 2)
        if count and stats_row.median_ppsf else None,
        avg_price_per_sqm=round(float(stats_row.avg_price_per_sqm or 0), 2) if count else 0.0,
    )


@app.get("/health")
@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
