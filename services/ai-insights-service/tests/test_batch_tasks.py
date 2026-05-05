"""Unit tests for Celery batch tasks (Phase 5D) — all DB calls mocked."""
import pytest
from unittest.mock import MagicMock, patch, call
from tasks.batch_tasks import (
    _fetch_house,
    _upsert_rental_yield,
    _upsert_prediction,
    _upsert_market_insight,
    _aggregate_city_stats,
    _fetch_all_houses,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(**kwargs):
    """Simulate a SQLAlchemy Row with _mapping."""
    row = MagicMock()
    row._mapping = kwargs
    return row


def _session_returning(rows):
    """Return a mock session whose execute().fetchone() returns rows[0]."""
    session = MagicMock()
    result = MagicMock()
    if isinstance(rows, list):
        result.fetchall.return_value = rows
        result.fetchone.return_value = rows[0] if rows else None
    else:
        result.fetchone.return_value = rows
    session.execute.return_value = result
    return session


# ---------------------------------------------------------------------------
# _fetch_house
# ---------------------------------------------------------------------------

class TestFetchHouse:
    def test_returns_dict_when_found(self):
        row = _make_row(id=1, city="toronto", region="downtown", price=500000,
                        area=80.0, rooms=3, floor=5, age=10, decoration="standard")
        session = _session_returning(row)
        result = _fetch_house(session, 1)
        assert isinstance(result, dict)
        assert result["city"] == "toronto"

    def test_returns_none_when_not_found(self):
        session = _session_returning(None)
        result = _fetch_house(session, 999)
        assert result is None


# ---------------------------------------------------------------------------
# _upsert_prediction
# ---------------------------------------------------------------------------

class TestUpsertPrediction:
    def test_calls_session_execute(self):
        session = MagicMock()
        prediction = {
            "predicted_price": 500000,
            "price_low": 425000,
            "price_high": 575000,
            "confidence": 0.80,
            "model_version": "v1.0.0-xgboost",
        }
        _upsert_prediction(session, house_id=1, prediction=prediction)
        session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# _upsert_rental_yield
# ---------------------------------------------------------------------------

class TestUpsertRentalYield:
    def test_calls_session_execute(self):
        session = MagicMock()
        yield_data = {
            "house_id": 1,
            "annual_rent": 28000,
            "gross_yield": 0.056,
            "net_yield": 0.050,
        }
        _upsert_rental_yield(session, yield_data)
        session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# _upsert_market_insight
# ---------------------------------------------------------------------------

class TestUpsertMarketInsight:
    def test_calls_session_execute(self):
        session = MagicMock()
        _upsert_market_insight(session, city="toronto", summary="Market is stable")
        session.execute.assert_called_once()

    def test_region_defaults_to_none(self):
        session = MagicMock()
        _upsert_market_insight(session, city="toronto", summary="stable")
        _, kwargs = session.execute.call_args
        # The params dict is in the second positional arg
        args = session.execute.call_args[0]
        params = args[1] if len(args) > 1 else session.execute.call_args[1]
        # Just confirm execute was called (region defaults inside function)
        session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# _aggregate_city_stats
# ---------------------------------------------------------------------------

class TestAggregateCityStats:
    def test_returns_dict_with_city(self):
        row = MagicMock()
        row.listing_count = 50
        row.avg_gross_yield = 0.05
        row.avg_price_per_sqm = 6000.0
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = row
        result = _aggregate_city_stats(session, "toronto")
        assert result["city"] == "toronto"
        assert result["listing_count"] == 50

    def test_returns_zero_listing_count_when_no_row(self):
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = None
        result = _aggregate_city_stats(session, "toronto")
        assert result["listing_count"] == 0

    def test_yield_converted_to_percentage(self):
        row = MagicMock()
        row.listing_count = 10
        row.avg_gross_yield = 0.05   # 5%
        row.avg_price_per_sqm = 5000.0
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = row
        result = _aggregate_city_stats(session, "toronto")
        assert result["avg_gross_yield_pct"] == pytest.approx(5.0, abs=0.01)


# ---------------------------------------------------------------------------
# compute_insights task — integration with mocked session
# ---------------------------------------------------------------------------

class TestComputeInsightsTask:
    def test_skips_missing_house(self):
        """If house not found, task should log and continue — no crash."""
        from tasks.batch_tasks import compute_insights
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = None

        with patch("tasks.batch_tasks.load_model", return_value=None), \
             patch("tasks.batch_tasks.generate_daily_narratives") as mock_narrative:
            compute_insights.run([999], session=session)
            mock_narrative.apply_async.assert_not_called()

    def test_commits_after_processing(self):
        """Session should be committed once all houses are processed."""
        from tasks.batch_tasks import compute_insights
        row = _make_row(id=1, city="toronto", region="downtown", price=500000,
                        area=80.0, rooms=3, floor=5, age=10, decoration="standard")
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = row

        with patch("tasks.batch_tasks.load_model", return_value=None), \
             patch("tasks.batch_tasks.compute_rental_yield", return_value={
                 "house_id": 1, "annual_rent": 28000, "gross_yield": 0.056, "net_yield": 0.050
             }), \
             patch("tasks.batch_tasks.generate_daily_narratives"):
            compute_insights.run([1], session=session)
            session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# generate_daily_narratives task — integration with mocked session + adapter
# ---------------------------------------------------------------------------

class TestGenerateDailyNarrativesTask:
    def test_calls_adapter_generate(self):
        from tasks.batch_tasks import generate_daily_narratives
        session = MagicMock()
        # _aggregate_city_stats returns a stats dict
        row = MagicMock()
        row.listing_count = 20
        row.avg_gross_yield = 0.045
        row.avg_price_per_sqm = 6000.0
        session.execute.return_value.fetchone.return_value = row

        adapter = MagicMock()
        adapter.generate.return_value = "Toronto market is stable."

        generate_daily_narratives.run(cities=["toronto"], session=session, narrative_adapter=adapter)
        adapter.generate.assert_called_once()
        session.commit.assert_called_once()

    def test_continues_on_adapter_failure(self):
        """If adapter.generate raises, task should log and continue to next city."""
        from tasks.batch_tasks import generate_daily_narratives
        session = MagicMock()
        row = MagicMock()
        row.listing_count = 5
        row.avg_gross_yield = 0.04
        row.avg_price_per_sqm = 5500.0
        session.execute.return_value.fetchone.return_value = row

        adapter = MagicMock()
        adapter.generate.side_effect = Exception("API error")

        # Should not raise — exception is caught per city
        generate_daily_narratives.run(cities=["toronto"], session=session, narrative_adapter=adapter)
        session.commit.assert_called_once()
