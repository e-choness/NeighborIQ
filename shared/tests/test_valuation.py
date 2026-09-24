"""Unit tests for comparable-listing valuation (no database)."""
import pytest

from shared.analytics.valuation import MIN_COMPS, select_comps, value_from_comps

SUBJECT = {"id": 1, "price": 800_000, "sqft": 1_000, "latitude": 43.65, "longitude": -79.38}


def _candidate(i: int, ppsf: float, dlat: float = 0.001) -> dict:
    return {
        "id": 100 + i, "title": f"comp {i}", "community": "Test", "rooms": 2,
        "price": int(ppsf * 900), "sqft": 900,
        "latitude": 43.65 + dlat * (i + 1), "longitude": -79.38,
    }


def test_selects_nearest_first_and_caps_count():
    candidates = [_candidate(i, 900) for i in range(12)]
    comps, radius = select_comps(SUBJECT, candidates)
    assert len(comps) == 8
    distances = [c.distance_m for c in comps]
    assert distances == sorted(distances)
    assert radius == 1500


def test_widens_radius_when_too_few_nearby():
    candidates = [_candidate(i, 900, dlat=0.02) for i in range(MIN_COMPS)]  # ~2.2 km apart
    comps, radius = select_comps(SUBJECT, candidates)
    assert radius > 1500 and len(comps) >= 1


def test_fair_value_is_median_ppsf_times_sqft():
    comps, radius = select_comps(SUBJECT, [_candidate(i, p) for i, p in enumerate([700, 800, 900, 1000, 1100])])
    v = value_from_comps(SUBJECT, comps, radius)
    assert v.median_price_per_sqft == pytest.approx(900, abs=1)
    assert v.fair_value == 900_000
    assert v.delta_pct == pytest.approx(-11.1, abs=0.1)
    assert v.verdict == "below"
    assert v.fair_value_low < v.fair_value < v.fair_value_high


@pytest.mark.parametrize("ask,verdict", [(900_000, "in_line"), (1_000_000, "above"), (800_000, "below")])
def test_verdict_bands(ask, verdict):
    comps, radius = select_comps(SUBJECT, [_candidate(i, 900) for i in range(6)])
    assert value_from_comps({**SUBJECT, "price": ask}, comps, radius).verdict == verdict


def test_confidence_reflects_count_and_dispersion():
    tight, r = select_comps(SUBJECT, [_candidate(i, 900 + i) for i in range(8)])
    assert value_from_comps(SUBJECT, tight, r).confidence == "high"
    spread, r = select_comps(SUBJECT, [_candidate(i, p) for i, p in enumerate([500, 900, 1300, 700, 1100])])
    assert value_from_comps(SUBJECT, spread, r).confidence == "low"


def test_no_valuation_without_evidence():
    comps, r = select_comps(SUBJECT, [_candidate(0, 900)])
    assert value_from_comps(SUBJECT, comps, r) is None
    assert value_from_comps({**SUBJECT, "sqft": None}, comps, r) is None
