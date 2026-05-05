"""Unit tests for narrative adapters (Phase 5C)."""
import pytest
from app.narrative import LocalNarrativeAdapter, get_adapter, _build_prompt


SAMPLE_STATS = {
    "city": "toronto",
    "listing_count": 150,
    "avg_gross_yield_pct": 4.5,
    "price_trend_pct": 2.3,
    "trend_direction": "upward",
    "top_region": "downtown",
    "top_neighborhoods": "downtown, midtown",
}


class TestLocalNarrativeAdapter:
    def test_returns_string(self):
        adapter = LocalNarrativeAdapter()
        result = adapter.generate(city="toronto", stats=SAMPLE_STATS)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_city_name(self):
        adapter = LocalNarrativeAdapter()
        result = adapter.generate(city="toronto", stats=SAMPLE_STATS)
        assert "Toronto" in result or "toronto" in result.lower()

    def test_contains_yield(self):
        adapter = LocalNarrativeAdapter()
        result = adapter.generate(city="toronto", stats=SAMPLE_STATS)
        assert "4.5" in result

    def test_contains_listing_count(self):
        adapter = LocalNarrativeAdapter()
        result = adapter.generate(city="toronto", stats=SAMPLE_STATS)
        assert "150" in result

    def test_upward_direction(self):
        adapter = LocalNarrativeAdapter()
        result = adapter.generate(city="toronto", stats={**SAMPLE_STATS, "price_trend_pct": 3.0})
        assert "upward" in result

    def test_downward_direction(self):
        adapter = LocalNarrativeAdapter()
        result = adapter.generate(city="toronto", stats={**SAMPLE_STATS, "price_trend_pct": -1.5})
        assert "downward" in result

    def test_empty_stats_does_not_raise(self):
        adapter = LocalNarrativeAdapter()
        result = adapter.generate(city="toronto", stats={})
        assert isinstance(result, str)

    def test_disclaimer_present(self):
        adapter = LocalNarrativeAdapter()
        result = adapter.generate(city="toronto", stats=SAMPLE_STATS)
        # Should recommend professional advice
        assert "real estate" in result.lower()


class TestGetAdapter:
    def test_default_returns_local(self, monkeypatch):
        monkeypatch.delenv("NARRATIVE_PROVIDER", raising=False)
        adapter = get_adapter()
        assert isinstance(adapter, LocalNarrativeAdapter)

    def test_explicit_local(self):
        adapter = get_adapter(provider="local")
        assert isinstance(adapter, LocalNarrativeAdapter)

    def test_azure_missing_keys_falls_back_to_local(self, monkeypatch):
        monkeypatch.setenv("NARRATIVE_PROVIDER", "azure")
        monkeypatch.delenv("AZURE_OPENAI_KEY", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        adapter = get_adapter(provider="azure")
        assert isinstance(adapter, LocalNarrativeAdapter)


class TestBuildPrompt:
    def test_contains_city(self):
        prompt = _build_prompt("toronto", SAMPLE_STATS)
        assert "Toronto" in prompt or "toronto" in prompt.lower()

    def test_contains_listing_count(self):
        prompt = _build_prompt("toronto", SAMPLE_STATS)
        assert "150" in prompt

    def test_contains_yield(self):
        prompt = _build_prompt("toronto", SAMPLE_STATS)
        assert "4.5" in prompt

    def test_instructs_no_hallucination(self):
        prompt = _build_prompt("toronto", SAMPLE_STATS)
        assert "Do not invent" in prompt or "do not invent" in prompt.lower()
