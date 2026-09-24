"""Unit tests for the Canadian rental cash-flow engine."""
import pytest

from shared.analytics.cashflow import (
    CashFlowInput,
    compute,
    insurance_premium_rate,
    land_transfer_tax,
    monthly_rate,
    mortgage_payment,
)


def test_semi_annual_compounding():
    # 5% nominal compounded semi-annually → effective annual 5.0625%
    assert (1 + monthly_rate(5.0)) ** 12 == pytest.approx(1.050625, rel=1e-9)


def test_mortgage_payment_matches_canadian_calculators():
    # $400,000, 5%, 25 years — Canadian (semi-annual) payment is ≈ $2,326.42
    assert mortgage_payment(400_000, 5.0, 25) == pytest.approx(2326.42, abs=0.5)


def test_zero_rate_is_straight_line():
    assert mortgage_payment(300_000, 0.0, 25) == pytest.approx(1000.0)


@pytest.mark.parametrize(
    "ltv,rate",
    [(0.80, 0.0), (0.85, 0.028), (0.90, 0.031), (0.95, 0.040), (0.851, 0.031)],
)
def test_insurance_premium_bands(ltv, rate):
    assert insurance_premium_rate(ltv) == rate


def test_ontario_ltt_known_value():
    # Ontario LTT on $500,000 = $6,475 (standard published example)
    tax, note = land_transfer_tax(500_000, "Ottawa")
    assert tax == pytest.approx(6475)
    assert "Ontario" in note


def test_toronto_pays_municipal_ltt_too():
    ottawa, _ = land_transfer_tax(500_000, "Ottawa")
    toronto, note = land_transfer_tax(500_000, "Toronto")
    assert toronto == pytest.approx(2 * ottawa)
    assert "Toronto" in note


def test_bc_ptt_known_value():
    # BC PTT on $1,000,000 = 1% of 200k + 2% of 800k = $18,000
    assert land_transfer_tax(1_000_000, "Vancouver")[0] == pytest.approx(18_000)


def test_alberta_has_no_ltt():
    tax, note = land_transfer_tax(500_000, "Calgary")
    assert tax < 500 and "no LTT" in note


def _inputs(**overrides) -> CashFlowInput:
    base = dict(
        price=500_000, monthly_rent=2_600, city="Calgary",
        down_payment_pct=20, interest_rate_pct=5.0, amortization_years=25,
        vacancy_pct=4, property_tax_annual=3_000, condo_fee_monthly=400,
        insurance_monthly=35, maintenance_pct=5, management_pct=0,
    )
    base.update(overrides)
    return CashFlowInput(**base)


def test_cash_flow_identity():
    r = compute(_inputs())
    assert r.down_payment == 100_000
    assert r.insurance_premium == 0
    expected = r.effective_monthly_income - r.monthly_operating_expenses - r.monthly_mortgage_payment
    assert r.monthly_cash_flow == pytest.approx(expected, abs=0.02)
    assert r.noi_annual == pytest.approx((r.effective_monthly_income - r.monthly_operating_expenses) * 12, abs=0.1)
    assert r.cap_rate_pct == pytest.approx(r.noi_annual / 500_000 * 100, abs=0.01)


def test_break_even_rent_zeroes_cash_flow():
    r = compute(_inputs())
    at_break_even = compute(_inputs(monthly_rent=r.break_even_rent))
    assert at_break_even.monthly_cash_flow == pytest.approx(0, abs=0.05)


def test_all_cash_purchase_has_no_debt():
    r = compute(_inputs(down_payment_pct=100))
    assert r.monthly_mortgage_payment == 0 and r.dscr is None
    assert r.monthly_cash_flow == pytest.approx(r.noi_annual / 12, abs=0.02)


def test_low_down_payment_adds_premium_and_warns():
    r = compute(_inputs(down_payment_pct=10))
    assert r.insurance_premium == pytest.approx(450_000 * 0.031)
    assert r.mortgage_principal == pytest.approx(450_000 * 1.031)
    assert any("insurance" in w for w in r.warnings)


def test_price_above_insured_cap_warns():
    r = compute(_inputs(price=1_600_000, down_payment_pct=10))
    assert any("1.5M" in w for w in r.warnings)


def test_negative_cash_flow_warns():
    assert any("Negative" in w for w in compute(_inputs(monthly_rent=1_000)).warnings)


def test_year_one_principal_paydown_is_positive_and_bounded():
    r = compute(_inputs())
    assert 0 < r.principal_paydown_year1 < r.monthly_mortgage_payment * 12


def test_closing_cost_override():
    r = compute(_inputs(closing_costs=12_345))
    assert r.closing_costs == 12_345 and r.cash_invested == 100_000 + 12_345
