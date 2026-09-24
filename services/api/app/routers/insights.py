"""
Investor analytics per listing and per market.

Listing: comparable-listing fair value, rent estimate, default cash flow and
(optionally) the backtested ML estimate. Market: city summaries and compact
listing points for the map. These endpoints are sync — FastAPI runs them in a
threadpool — and share the analytics code the insights worker uses in batch.
"""
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.analytics.cashflow import (
    CashFlowInput,
    CashFlowResult,
    compute as compute_cash_flow,
    default_insurance_monthly,
    default_maintenance_pct,
)
from shared.analytics.valuation import (
    RentEstimate,
    Valuation,
    fetch_subject,
    rent_estimate_for,
    valuation_for,
)
from shared.database.sync import get_sync_db

router = APIRouter(tags=["insights"])


def ml_predictions_enabled() -> bool:
    return os.getenv("ML_PREDICTIONS_ENABLED", "0") == "1"


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


class RateContext(BaseModel):
    rate_pct: float
    series: str
    label: str
    date: str
    note: str = (
        "Bank of Canada posted 5-year conventional rate — a conservative default. "
        "Negotiated rates are usually lower; enter yours."
    )


class AreaContext(BaseModel):
    id: int
    name: str
    stats: dict


class HouseInsightsResponse(BaseModel):
    house_id: int
    is_synthetic: bool = False
    area: Optional[AreaContext] = None
    rate: Optional[RateContext] = None
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


MORTGAGE_RATE_SERIES = "boc:V80691335"


def latest_mortgage_rate(db: Session) -> Optional[RateContext]:
    if not db.execute(text("SELECT to_regclass('od_indicators')")).scalar():
        return None
    row = db.execute(text("""
        SELECT value, label, date FROM od_indicators WHERE series = :s ORDER BY date DESC LIMIT 1
    """), {"s": MORTGAGE_RATE_SERIES}).fetchone()
    if row is None:
        return None
    return RateContext(rate_pct=row.value, series=MORTGAGE_RATE_SERIES, label=row.label or "", date=row.date.isoformat())


def area_context(db: Session, area_id: Optional[int]) -> Optional[AreaContext]:
    if not area_id:
        return None
    name = db.execute(text("SELECT name FROM od_areas WHERE id = :id"), {"id": area_id}).scalar()
    if name is None:
        return None
    stats = {
        r.metric: {"value": r.value, "period": r.period or None}
        for r in db.execute(text("""
            SELECT DISTINCT ON (metric) metric, period, value FROM od_area_stats
            WHERE area_id = :id ORDER BY metric, period DESC
        """), {"id": area_id})
    }
    return AreaContext(id=area_id, name=name, stats=stats)


def default_cash_flow_inputs(
    subject: dict, rent: Optional[RentEstimate], rate: Optional[RateContext] = None
) -> CashFlowInput:
    """Investor defaults for a listing — every value is editable in the UI."""
    ptype = subject.get("property_type")
    rate_kwargs = {"interest_rate_pct": rate.rate_pct} if rate else {}
    return CashFlowInput(
        **rate_kwargs,
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

@router.get("/api/v1/houses/{house_id}/insights", response_model=HouseInsightsResponse)
def get_house_insights(house_id: int, db: Session = Depends(get_sync_db)):
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
    rate = latest_mortgage_rate(db)
    inputs = default_cash_flow_inputs(subject, rent, rate)
    cash_flow = CashFlowSummary(inputs=inputs, result=compute_cash_flow(inputs)) if rent else None
    ml = _latest_ml_prediction(db, house_id)

    return HouseInsightsResponse(
        house_id=house_id,
        is_synthetic=bool(subject.get("is_synthetic")),
        area=area_context(db, subject.get("area_id")),
        rate=rate,
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


@router.get("/api/v1/houses/{house_id}/valuation", response_model=Optional[Valuation])
def get_house_valuation(house_id: int, db: Session = Depends(get_sync_db)):
    """Comparable-listing valuation only. null = not enough comparable listings."""
    subject = fetch_subject(db, house_id)
    if subject is None:
        raise HTTPException(status_code=404, detail=f"House {house_id} not found")
    return valuation_for(db, subject)


class AdHocSubject(BaseModel):
    """A property that is not a listing — for the deal analyzer."""
    city: str
    price: int
    sqft: int
    latitude: float
    longitude: float
    property_type: Optional[str] = None
    rooms: Optional[int] = None


@router.post("/api/v1/valuation", response_model=Optional[Valuation])
def post_valuation(subject: AdHocSubject, db: Session = Depends(get_sync_db)):
    """Comparable-listing valuation for any property. null = not enough comparables."""
    return valuation_for(db, {"id": 0, **subject.model_dump()})


@router.get("/api/v1/rents", response_model=Optional[RentEstimate])
def get_rent_benchmark(city: str, bedrooms: int = Query(ge=0, le=10), db: Session = Depends(get_sync_db)):
    """Benchmark monthly rent for a city and bedroom count (3 = three or more)."""
    return rent_estimate_for(db, city, bedrooms)


@router.get("/api/v1/cashflow/defaults")
def cash_flow_defaults(db: Session = Depends(get_sync_db)):
    """Default assumptions for a blank analysis (rate from the Bank of Canada when loaded)."""
    rate = latest_mortgage_rate(db)
    base = CashFlowInput(price=1, monthly_rent=0)
    return {
        "inputs": base.model_dump(exclude={"price", "monthly_rent", "city"}) | (
            {"interest_rate_pct": rate.rate_pct} if rate else {}
        ),
        "rate": rate,
    }


@router.post("/api/v1/cashflow", response_model=CashFlowResult)
def post_cash_flow(inputs: CashFlowInput):
    """Stateless cash-flow projection for user-edited assumptions."""
    return compute_cash_flow(inputs)


@router.get("/api/v1/neighborhoods/{city}/{region}/analysis", response_model=NeighborhoodAnalysisResponse)
def get_neighborhood_analysis(city: str, region: str, db: Session = Depends(get_sync_db)):
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




# ---------------------------------------------------------------------------
# Markets — what the home page and map show
# ---------------------------------------------------------------------------

class MarketSummary(BaseModel):
    city: str
    listing_count: int
    median_price: Optional[int]
    median_price_per_sqft: Optional[float]
    median_gross_yield_pct: Optional[float]
    median_cap_rate_pct: Optional[float]
    price_cut_share_pct: Optional[float]
    median_days_on_market: Optional[int]
    synthetic_share_pct: float
    latitude: Optional[float]
    longitude: Optional[float]


_MARKETS_SQL = text("""
    WITH active AS (
        SELECT h.*,
               (SELECT p.price FROM house_price_history p
                WHERE p.house_id = h.id ORDER BY p.recorded_at, p.id LIMIT 1) AS first_price
        FROM house_houses h
        WHERE h.is_active = 1 AND (CAST(:city AS TEXT) IS NULL OR LOWER(h.city) = LOWER(:city))
    )
    SELECT a.city,
           COUNT(*)                                                               AS listing_count,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY a.price)                   AS median_price,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY a.price::numeric / NULLIF(a.sqft, 0))
                                                                                  AS median_ppsf,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ry.gross_yield)            AS median_gross_yield,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ry.net_yield)              AS median_cap_rate,
           AVG(CASE WHEN a.first_price > a.price THEN 100.0 ELSE 0.0 END)         AS price_cut_share,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(DAY FROM NOW() - a.listed_at))
                                                                                  AS median_dom,
           AVG(a.is_synthetic) * 100                                              AS synthetic_share,
           AVG(a.latitude)                                                        AS latitude,
           AVG(a.longitude)                                                       AS longitude
    FROM active a
    LEFT JOIN house_rental_yields ry ON ry.house_id = a.id
    GROUP BY a.city
    ORDER BY COUNT(*) DESC
""")


def _num(v, digits=2):
    return round(float(v), digits) if v is not None else None


@router.get("/api/v1/markets", response_model=list[MarketSummary])
def list_markets(city: Optional[str] = None, db: Session = Depends(get_sync_db)):
    """Per-city market snapshot computed from active listings."""
    rows = db.execute(_MARKETS_SQL, {"city": city}).mappings().all()
    return [
        MarketSummary(
            city=r["city"],
            listing_count=int(r["listing_count"]),
            median_price=int(r["median_price"]) if r["median_price"] is not None else None,
            median_price_per_sqft=_num(r["median_ppsf"]),
            median_gross_yield_pct=_num(r["median_gross_yield"] * 100) if r["median_gross_yield"] is not None else None,
            median_cap_rate_pct=_num(r["median_cap_rate"] * 100) if r["median_cap_rate"] is not None else None,
            price_cut_share_pct=_num(r["price_cut_share"], 1),
            median_days_on_market=int(r["median_dom"]) if r["median_dom"] is not None else None,
            synthetic_share_pct=_num(r["synthetic_share"], 1) or 0.0,
            latitude=_num(r["latitude"], 5),
            longitude=_num(r["longitude"], 5),
        )
        for r in rows
    ]


@router.get("/api/v1/markets/{city}/points")
def market_points(
    city: str,
    limit: int = Query(default=5000, ge=1, le=20000),
    db: Session = Depends(get_sync_db),
):
    """
    Compact per-listing values for map aggregation (hexagons, heat, extrusions):
    columns = [id, lat, lon, price, price_per_sqft, gross_yield_pct, cap_rate_pct,
    price_cut_pct, days_on_market]. Arrays, not objects, to keep the payload small.
    """
    rows = db.execute(text("""
        SELECT h.id, h.latitude, h.longitude, h.price,
               h.price::numeric / NULLIF(h.sqft, 0)                           AS ppsf,
               ry.gross_yield * 100                                           AS gross_yield,
               ry.net_yield * 100                                             AS cap_rate,
               (SELECT (p.price - h.price)::numeric * 100 / p.price
                FROM house_price_history p WHERE p.house_id = h.id
                ORDER BY p.recorded_at, p.id LIMIT 1)                         AS cut_pct,
               EXTRACT(DAY FROM NOW() - h.listed_at)                          AS dom
        FROM house_houses h
        LEFT JOIN house_rental_yields ry ON ry.house_id = h.id
        WHERE h.is_active = 1 AND LOWER(h.city) = LOWER(:city) AND h.latitude IS NOT NULL
        ORDER BY h.id
        LIMIT :limit
    """), {"city": city, "limit": limit}).fetchall()
    columns = ["id", "lat", "lon", "price", "price_per_sqft", "gross_yield_pct",
               "cap_rate_pct", "price_cut_pct", "days_on_market"]
    return {
        "city": city,
        "columns": columns,
        "rows": [
            [r.id, float(r.latitude), float(r.longitude), r.price,
             _num(r.ppsf, 0), _num(r.gross_yield), _num(r.cap_rate),
             max(0.0, _num(r.cut_pct, 1) or 0.0), int(r.dom) if r.dom is not None else None]
            for r in rows
        ],
    }
