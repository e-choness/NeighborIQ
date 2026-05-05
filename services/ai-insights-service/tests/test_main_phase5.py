"""
Tests for Phase 5E API endpoints.
Uses FastAPI dependency_overrides to inject mock DB sessions — no live DB required.
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app, get_db


# ---------------------------------------------------------------------------
# Session mock helpers
# ---------------------------------------------------------------------------

def _row(**kwargs):
    """Build a mock row with attribute access."""
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


def _make_db_override(pred_row=None, yield_row=None, insight_row=None, stats_row=None):
    """
    Returns an override for get_db that yields a mock session.
    Call order per endpoint:
      - get_house_insights       : fetchone() twice (pred, yield)
      - get_neighborhood_analysis: fetchone() twice (insight, stats)
    """
    call_count = {"n": 0}

    def override():
        session = MagicMock()

        fetchone_returns = []
        if pred_row is not None or yield_row is not None:
            fetchone_returns = [pred_row, yield_row]
        elif insight_row is not None or stats_row is not None:
            fetchone_returns = [insight_row, stats_row]

        results = [MagicMock() for _ in fetchone_returns]
        for r, val in zip(results, fetchone_returns):
            r.fetchone.return_value = val

        iter_results = iter(results)

        def execute_side_effect(*args, **kwargs):
            try:
                return next(iter_results)
            except StopIteration:
                m = MagicMock()
                m.fetchone.return_value = None
                return m

        session.execute.side_effect = execute_side_effect
        yield session

    return override


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/v1/health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_returns_ok(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /api/v1/houses/{house_id}/insights
# ---------------------------------------------------------------------------

class TestHouseInsights:
    def test_404_when_no_data(self, client):
        app.dependency_overrides[get_db] = _make_db_override(pred_row=None, yield_row=None)
        r = client.get("/api/v1/houses/99999/insights")
        assert r.status_code == 404
        assert "No insights found" in r.json()["detail"]

    def test_200_with_prediction_only(self, client):
        pred = _row(predicted_price=500000, price_low=425000, price_high=575000,
                    confidence=0.80, model_version="v1.0.0-xgboost")
        app.dependency_overrides[get_db] = _make_db_override(pred_row=pred, yield_row=None)
        r = client.get("/api/v1/houses/1/insights")
        assert r.status_code == 200
        data = r.json()
        assert data["house_id"] == 1
        assert data["predicted_price"] == 500000
        assert data["gross_yield"] is None

    def test_200_with_yield_only(self, client):
        yield_row = _row(annual_rent=28000, gross_yield=0.056, net_yield=0.050)
        app.dependency_overrides[get_db] = _make_db_override(pred_row=None, yield_row=yield_row)
        r = client.get("/api/v1/houses/1/insights")
        assert r.status_code == 200
        data = r.json()
        assert data["house_id"] == 1
        assert data["annual_rent"] == 28000
        assert data["predicted_price"] is None

    def test_200_with_both(self, client):
        pred = _row(predicted_price=500000, price_low=425000, price_high=575000,
                    confidence=0.80, model_version="v1.0.0-xgboost")
        yield_row = _row(annual_rent=28000, gross_yield=0.056, net_yield=0.050)
        app.dependency_overrides[get_db] = _make_db_override(pred_row=pred, yield_row=yield_row)
        r = client.get("/api/v1/houses/1/insights")
        assert r.status_code == 200
        data = r.json()
        assert data["predicted_price"] == 500000
        assert data["gross_yield"] == pytest.approx(0.056)

    def test_response_shape(self, client):
        pred = _row(predicted_price=600000, price_low=510000, price_high=690000,
                    confidence=0.80, model_version="v1")
        yield_row = _row(annual_rent=30000, gross_yield=0.05, net_yield=0.045)
        app.dependency_overrides[get_db] = _make_db_override(pred_row=pred, yield_row=yield_row)
        r = client.get("/api/v1/houses/42/insights")
        data = r.json()
        assert data["house_id"] == 42
        assert set(data.keys()) == {
            "house_id", "predicted_price", "price_low", "price_high",
            "confidence", "model_version", "annual_rent", "gross_yield", "net_yield",
        }


# ---------------------------------------------------------------------------
# GET /api/v1/neighborhoods/{city}/{region}/analysis
# ---------------------------------------------------------------------------

class TestNeighborhoodAnalysis:
    def test_200_no_insights_returns_empty_summary(self, client):
        stats = _row(listing_count=10, avg_gross_yield=0.05, avg_price_per_sqm=6000.0)
        app.dependency_overrides[get_db] = _make_db_override(insight_row=None, stats_row=stats)
        r = client.get("/api/v1/neighborhoods/toronto/downtown/analysis")
        assert r.status_code == 200
        data = r.json()
        assert data["city"] == "toronto"
        assert data["region"] == "downtown"
        assert data["market_summary"] is None

    def test_200_with_insight(self, client):
        insight = _row(summary_text="Market is growing strongly.")
        stats = _row(listing_count=50, avg_gross_yield=0.045, avg_price_per_sqm=7000.0)
        app.dependency_overrides[get_db] = _make_db_override(insight_row=insight, stats_row=stats)
        r = client.get("/api/v1/neighborhoods/toronto/downtown/analysis")
        assert r.status_code == 200
        data = r.json()
        assert data["market_summary"] == "Market is growing strongly."
        assert data["listing_count"] == 50

    def test_yield_pct_converted(self, client):
        insight = _row(summary_text="")
        stats = _row(listing_count=20, avg_gross_yield=0.05, avg_price_per_sqm=5000.0)
        app.dependency_overrides[get_db] = _make_db_override(insight_row=insight, stats_row=stats)
        r = client.get("/api/v1/neighborhoods/vancouver/westside/analysis")
        data = r.json()
        # avg_gross_yield=0.05 → avg_gross_yield_pct should be 5.0
        assert data["avg_gross_yield_pct"] == pytest.approx(5.0, abs=0.01)

    def test_response_shape(self, client):
        stats = _row(listing_count=0, avg_gross_yield=None, avg_price_per_sqm=None)
        app.dependency_overrides[get_db] = _make_db_override(insight_row=None, stats_row=stats)
        r = client.get("/api/v1/neighborhoods/calgary/nw/analysis")
        data = r.json()
        assert set(data.keys()) == {
            "city", "region", "market_summary",
            "listing_count", "avg_gross_yield_pct", "avg_price_per_sqm",
        }

    def test_none_stats_defaults_to_zeros(self, client):
        app.dependency_overrides[get_db] = _make_db_override(insight_row=None, stats_row=None)
        r = client.get("/api/v1/neighborhoods/montreal/plateau/analysis")
        assert r.status_code == 200
        data = r.json()
        assert data["listing_count"] == 0
        assert data["avg_gross_yield_pct"] == 0.0


# ---------------------------------------------------------------------------
# Phase 3 endpoints — regression guard
# ---------------------------------------------------------------------------

class TestPhase3Regression:
    def test_predict_local(self, client):
        r = client.post("/api/v1/ai/predict", json={
            "provider": "local",
            "input": {"city": "toronto", "median_income": 80000},
        })
        assert r.status_code == 200
        assert "predictions" in r.json()

    def test_narrative_local(self, client):
        r = client.post("/api/v1/ai/narrative", json={
            "provider": "local",
            "input": {"city": "toronto"},
        })
        assert r.status_code == 200
        assert "text" in r.json()

    def test_unknown_provider_returns_400(self, client):
        r = client.post("/api/v1/ai/predict", json={
            "provider": "nonexistent",
            "input": {},
        })
        assert r.status_code == 400
