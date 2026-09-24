"""
Rental-property cash-flow calculator (Canadian conventions).

Deterministic and transparent: every output is derived from the inputs shown to
the user, who can edit any assumption. No ML.

Canadian specifics:
  - Fixed-rate mortgages compound semi-annually (Interest Act), so the monthly
    rate is (1 + r/2)^(1/6) − 1, not r/12.
  - Down payments under 20% need mortgage default insurance; the premium is
    added to the principal. Insured mortgages are capped at a $1.5M purchase
    price and are generally unavailable for non-owner-occupied rentals — we
    compute the premium but warn.
  - Land transfer tax is estimated per province (plus Toronto's municipal tax)
    and counted as cash invested. Estimates only; not legal or tax advice.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

# CMHC premium as a share of the loan, by loan-to-value band (upper bound inclusive)
_INSURANCE_PREMIUMS = ((0.85, 0.028), (0.90, 0.031), (0.95, 0.040))
INSURED_PRICE_CAP = 1_500_000

# Marginal brackets: (threshold, rate) — rate applies to the portion above threshold
_ONTARIO_LTT = ((0, 0.005), (55_000, 0.01), (250_000, 0.015), (400_000, 0.02), (2_000_000, 0.025))
_BC_PTT = ((0, 0.01), (200_000, 0.02), (2_000_000, 0.03), (3_000_000, 0.05))
# Québec "welcome tax" — approximate Montréal brackets (indexed yearly; verify before relying on it)
_QUEBEC_WELCOME = ((0, 0.005), (61_500, 0.01), (307_800, 0.015), (552_300, 0.02), (1_104_700, 0.025), (2_136_500, 0.035))

_CITY_PROVINCE = {
    "toronto": "ON", "ottawa": "ON", "mississauga": "ON", "hamilton": "ON",
    "vancouver": "BC", "burnaby": "BC", "victoria": "BC",
    "calgary": "AB", "edmonton": "AB",
    "montreal": "QC", "montréal": "QC", "quebec": "QC",
    "winnipeg": "MB",
}


def _bracketed(price: float, brackets) -> float:
    tax = 0.0
    for i, (threshold, rate) in enumerate(brackets):
        upper = brackets[i + 1][0] if i + 1 < len(brackets) else float("inf")
        if price > threshold:
            tax += (min(price, upper) - threshold) * rate
    return tax


def land_transfer_tax(price: float, city: str) -> tuple[float, str]:
    """Estimated land transfer tax and a short description of how it was computed."""
    key = (city or "").strip().lower()
    province = _CITY_PROVINCE.get(key)
    if province == "ON":
        tax = _bracketed(price, _ONTARIO_LTT)
        if key == "toronto":
            return tax * 2, "Ontario LTT + Toronto municipal LTT (same brackets up to $3M)"
        return tax, "Ontario land transfer tax"
    if province == "BC":
        return _bracketed(price, _BC_PTT), "BC property transfer tax"
    if province == "QC":
        return _bracketed(price, _QUEBEC_WELCOME), "Québec welcome tax (approx. Montréal brackets)"
    if province == "AB":
        # Alberta has no LTT — only land-title and mortgage registration fees
        return 50 + price / 5000 * 2, "Alberta title registration fees (no LTT)"
    return price * 0.015, "Rough 1.5% estimate (province not modelled)"


def monthly_rate(annual_rate_pct: float) -> float:
    """Monthly rate for a Canadian fixed mortgage (semi-annual compounding)."""
    return (1 + annual_rate_pct / 100 / 2) ** (1 / 6) - 1


def mortgage_payment(principal: float, annual_rate_pct: float, amortization_years: int) -> float:
    n = amortization_years * 12
    if principal <= 0:
        return 0.0
    i = monthly_rate(annual_rate_pct)
    if i == 0:
        return principal / n
    return principal * i / (1 - (1 + i) ** -n)


def insurance_premium_rate(loan_to_value: float) -> float:
    if loan_to_value <= 0.80:
        return 0.0
    for ltv_cap, rate in _INSURANCE_PREMIUMS:
        if loan_to_value <= ltv_cap + 1e-9:
            return rate
    return _INSURANCE_PREMIUMS[-1][1]


class CashFlowInput(BaseModel):
    price: float = Field(..., gt=0, description="Purchase price, CAD")
    monthly_rent: float = Field(..., ge=0)
    city: str = ""
    down_payment_pct: float = Field(20.0, ge=5, le=100)
    interest_rate_pct: float = Field(4.5, ge=0, le=25, description="Fixed rate, e.g. 4.5 for 4.5%")
    amortization_years: int = Field(25, ge=5, le=35)
    vacancy_pct: float = Field(4.0, ge=0, le=100)
    property_tax_annual: float = Field(0.0, ge=0)
    condo_fee_monthly: float = Field(0.0, ge=0)
    insurance_monthly: float = Field(0.0, ge=0)
    maintenance_pct: float = Field(5.0, ge=0, le=100, description="Share of rent reserved for repairs")
    management_pct: float = Field(0.0, ge=0, le=100, description="Property manager fee, share of rent")
    other_income_monthly: float = Field(0.0, ge=0, description="Parking, storage, laundry…")
    closing_costs: Optional[float] = Field(
        None, ge=0, description="Override; default = land transfer tax estimate + $2,000 legal/inspection"
    )


class CashFlowResult(BaseModel):
    down_payment: float
    insurance_premium: float
    mortgage_principal: float
    monthly_mortgage_payment: float
    closing_costs: float
    closing_costs_note: str
    cash_invested: float
    gross_monthly_income: float
    effective_monthly_income: float  # after vacancy
    monthly_expenses: dict[str, float]
    monthly_operating_expenses: float
    noi_annual: float
    monthly_cash_flow: float
    annual_cash_flow: float
    cap_rate_pct: float
    gross_yield_pct: float
    cash_on_cash_pct: float
    dscr: Optional[float]
    break_even_rent: Optional[float]
    principal_paydown_year1: float
    warnings: list[str]


def compute(inp: CashFlowInput) -> CashFlowResult:
    warnings: list[str] = []

    down = inp.price * inp.down_payment_pct / 100
    loan = inp.price - down
    ltv = loan / inp.price
    premium = loan * insurance_premium_rate(ltv)
    if premium:
        warnings.append(
            "Under 20% down requires mortgage default insurance; insured mortgages are "
            "generally only available for owner-occupied homes, not pure rentals."
        )
        if inp.price >= INSURED_PRICE_CAP:
            warnings.append("Insured mortgages are unavailable at $1.5M and above — 20% down required.")
    principal = loan + premium
    payment = mortgage_payment(principal, inp.interest_rate_pct, inp.amortization_years)

    if inp.closing_costs is not None:
        closing, closing_note = inp.closing_costs, "Entered by user"
    else:
        ltt, ltt_note = land_transfer_tax(inp.price, inp.city)
        closing = ltt + 2000
        closing_note = f"{ltt_note} + $2,000 legal/inspection (estimate)"

    gross_income = inp.monthly_rent + inp.other_income_monthly
    effective_income = gross_income * (1 - inp.vacancy_pct / 100)
    expenses = {
        "property_tax": inp.property_tax_annual / 12,
        "condo_fee": inp.condo_fee_monthly,
        "insurance": inp.insurance_monthly,
        "maintenance": inp.monthly_rent * inp.maintenance_pct / 100,
        "management": inp.monthly_rent * inp.management_pct / 100,
    }
    opex = sum(expenses.values())
    noi_monthly = effective_income - opex
    cash_flow = noi_monthly - payment
    cash_invested = down + closing

    annual_debt = payment * 12
    variable_share = 1 - inp.vacancy_pct / 100 - (inp.maintenance_pct + inp.management_pct) / 100
    fixed = expenses["property_tax"] + expenses["condo_fee"] + expenses["insurance"] + payment
    other = inp.other_income_monthly * (1 - inp.vacancy_pct / 100)
    break_even = (fixed - other) / variable_share if variable_share > 0 else None

    # Equity built in year one: principal repaid across the first 12 payments
    balance, i = principal, monthly_rate(inp.interest_rate_pct)
    for _ in range(min(12, inp.amortization_years * 12)):
        balance -= payment - balance * i

    if inp.monthly_rent == 0:
        warnings.append("No rent entered — returns are meaningless until you add one.")
    if cash_flow < 0:
        warnings.append("Negative monthly cash flow at these assumptions.")

    return CashFlowResult(
        down_payment=round(down, 2),
        insurance_premium=round(premium, 2),
        mortgage_principal=round(principal, 2),
        monthly_mortgage_payment=round(payment, 2),
        closing_costs=round(closing, 2),
        closing_costs_note=closing_note,
        cash_invested=round(cash_invested, 2),
        gross_monthly_income=round(gross_income, 2),
        effective_monthly_income=round(effective_income, 2),
        monthly_expenses={k: round(v, 2) for k, v in expenses.items()},
        monthly_operating_expenses=round(opex, 2),
        noi_annual=round(noi_monthly * 12, 2),
        monthly_cash_flow=round(cash_flow, 2),
        annual_cash_flow=round(cash_flow * 12, 2),
        cap_rate_pct=round(noi_monthly * 12 / inp.price * 100, 2),
        gross_yield_pct=round(inp.monthly_rent * 12 / inp.price * 100, 2),
        cash_on_cash_pct=round(cash_flow * 12 / cash_invested * 100, 2) if cash_invested else 0.0,
        dscr=round(noi_monthly * 12 / annual_debt, 2) if annual_debt else None,
        break_even_rent=round(break_even, 2) if break_even is not None else None,
        principal_paydown_year1=round(principal - balance, 2),
        warnings=warnings,
    )


def default_insurance_monthly(property_type: Optional[str]) -> float:
    """Landlord insurance placeholder: condo unit policy vs. freehold building policy."""
    return 35.0 if property_type == "condo" else 125.0


def default_maintenance_pct(property_type: Optional[str], age: Optional[int]) -> float:
    base = 5.0 if property_type == "condo" else 8.0  # condo fees already fund common elements
    if age and age > 40:
        base += 2.0
    return base
