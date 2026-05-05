from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
import os

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
# Phase 3 — provider-agnostic request/response models
# ---------------------------------------------------------------------------

class AIProviderRequest(BaseModel):
    provider: str = Field(
        ..., description="Provider identifier, e.g., 'azure', 'openai', 'local'", json_schema_extra={"example": "local"})
    model: Optional[str] = Field(
        None, description="Optional model name", json_schema_extra={"example": "gpt-4o-mini"})
    input: Dict[str, Any] = Field(..., description="Domain-specific input (features or city descriptor)",
                                  json_schema_extra={"example": {"city": "Austin", "median_income": 80000}})
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Provider-specific options", json_schema_extra={"example": {"max_tokens": 200, "temperature": 0.2}})
    async_callback_url: Optional[str] = Field(
        None, description="Optional callback URL for async results", json_schema_extra={"example": None})


class AIProviderPredictionResponse(BaseModel):
    provider: str
    model: Optional[str]
    predictions: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class AIProviderTextResponse(BaseModel):
    provider: str
    model: Optional[str]
    text: str
    tokens_used: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Phase 5E — insights response models
# ---------------------------------------------------------------------------

class HouseInsightsResponse(BaseModel):
    house_id: int
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
    avg_gross_yield_pct: float = 0.0
    avg_price_per_sqm: float = 0.0


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="AI Insights Service", version="0.2.0")


# ---------------------------------------------------------------------------
# Phase 3 — provider adapter registry
# ---------------------------------------------------------------------------

class ProviderAdapter:
    def predict(self, input: Dict[str, Any], parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raise NotImplementedError()

    def narrative(self, input: Dict[str, Any], parameters: Optional[Dict[str, Any]] = None) -> str:
        raise NotImplementedError()


class LocalAdapter(ProviderAdapter):
    def predict(self, input: Dict[str, Any], parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        city = input.get("city", "unknown")
        base = 300000 if city.lower() != "unknown" else 100000
        price = base + int(input.get("median_income", 50000) / 10)
        return {"price": price, "rental_yield": 0.05}

    def narrative(self, input: Dict[str, Any], parameters: Optional[Dict[str, Any]] = None) -> str:
        city = input.get("city", "your area")
        return f"Market narrative for {city}: stable demand with moderate price growth."


ADAPTERS = {
    "local": LocalAdapter(),
}


def _get_adapter(provider: str) -> ProviderAdapter:
    adapter = ADAPTERS.get(provider)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    return adapter


# ---------------------------------------------------------------------------
# Phase 3 endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/ai/predict", response_model=AIProviderPredictionResponse)
async def ai_predict(req: AIProviderRequest):
    adapter = _get_adapter(req.provider)
    predictions = adapter.predict(req.input, req.parameters)
    return AIProviderPredictionResponse(
        provider=req.provider, model=req.model, predictions=predictions,
        metadata={"source": "local-stub"},
    )


@app.post("/api/v1/ai/narrative", response_model=AIProviderTextResponse)
async def ai_narrative(req: AIProviderRequest):
    adapter = _get_adapter(req.provider)
    text = adapter.narrative(req.input, req.parameters)
    return AIProviderTextResponse(
        provider=req.provider, model=req.model, text=text,
        tokens_used=0, metadata={"source": "local-stub"},
    )


# ---------------------------------------------------------------------------
# Phase 5E endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/houses/{house_id}/insights", response_model=HouseInsightsResponse)
def get_house_insights(house_id: int, db: Session = Depends(get_db)):
    pred_row = db.execute(
        text("""
            SELECT predicted_price, price_low, price_high, confidence, model_version
            FROM house_price_predictions
            WHERE house_id = :house_id
            ORDER BY predicted_at DESC
            LIMIT 1
        """),
        {"house_id": house_id},
    ).fetchone()

    yield_row = db.execute(
        text("""
            SELECT annual_rent, gross_yield, net_yield
            FROM house_rental_yields
            WHERE house_id = :house_id
        """),
        {"house_id": house_id},
    ).fetchone()

    if pred_row is None and yield_row is None:
        raise HTTPException(status_code=404, detail=f"No insights found for house_id={house_id}")

    return HouseInsightsResponse(
        house_id=house_id,
        predicted_price=pred_row.predicted_price if pred_row else None,
        price_low=pred_row.price_low if pred_row else None,
        price_high=pred_row.price_high if pred_row else None,
        confidence=pred_row.confidence if pred_row else None,
        model_version=pred_row.model_version if pred_row else None,
        annual_rent=yield_row.annual_rent if yield_row else None,
        gross_yield=yield_row.gross_yield if yield_row else None,
        net_yield=yield_row.net_yield if yield_row else None,
    )


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
                COUNT(h.id)                                         AS listing_count,
                AVG(ry.gross_yield)                                 AS avg_gross_yield,
                AVG(h.price::numeric / NULLIF(h.area, 0))           AS avg_price_per_sqm
            FROM house_houses h
            LEFT JOIN house_rental_yields ry ON ry.house_id = h.id
            WHERE LOWER(h.city) = LOWER(:city)
              AND LOWER(h.region) = LOWER(:region)
              AND h.is_active = 1
        """),
        {"city": city, "region": region},
    ).fetchone()

    listing_count = int(stats_row.listing_count or 0) if stats_row else 0
    avg_yield_pct = round(float(stats_row.avg_gross_yield or 0) * 100, 2) if stats_row else 0.0
    avg_price_sqm = round(float(stats_row.avg_price_per_sqm or 0), 2) if stats_row else 0.0

    return NeighborhoodAnalysisResponse(
        city=city,
        region=region,
        market_summary=insight_row.summary_text if insight_row else None,
        listing_count=listing_count,
        avg_gross_yield_pct=avg_yield_pct,
        avg_price_per_sqm=avg_price_sqm,
    )


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
