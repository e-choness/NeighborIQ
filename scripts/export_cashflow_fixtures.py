"""
Write the cash-flow fixtures shared by the Python calculator and its JavaScript
port in the docs (docs/.vitepress/theme/lib/cashflow.js).

    python scripts/export_cashflow_fixtures.py

shared/tests/test_cashflow_fixtures.py fails when the Python output drifts from
the fixtures; docs/scripts/check-cashflow.mjs fails when the JavaScript does.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.analytics.cashflow import CashFlowInput, compute  # noqa: E402

FIXTURES = ROOT / "docs" / ".vitepress" / "theme" / "lib" / "cashflow.fixtures.json"

CASES = [
    {
        "price": 650_000,
        "monthly_rent": 2_900,
        "city": "Toronto",
        "property_tax_annual": 3_900,
        "condo_fee_monthly": 520,
        "insurance_monthly": 35,
    },
    {
        "price": 1_250_000,
        "monthly_rent": 4_800,
        "city": "Vancouver",
        "down_payment_pct": 25,
        "interest_rate_pct": 5.19,
        "property_tax_annual": 4_300,
        "insurance_monthly": 125,
        "maintenance_pct": 8,
    },
    {
        "price": 420_000,
        "monthly_rent": 2_300,
        "city": "Calgary",
        "down_payment_pct": 10,
        "amortization_years": 30,
        "property_tax_annual": 2_700,
        "condo_fee_monthly": 380,
    },
    {
        "price": 1_600_000,
        "monthly_rent": 5_200,
        "city": "Toronto",
        "down_payment_pct": 5,
        "management_pct": 8,
    },
    {
        "price": 540_000,
        "monthly_rent": 2_450,
        "city": "Montreal",
        "vacancy_pct": 3,
        "other_income_monthly": 100,
        "closing_costs": 9_000,
    },
    {"price": 720_000, "monthly_rent": 0, "city": "Ottawa", "interest_rate_pct": 0},
    {"price": 380_000, "monthly_rent": 2_100, "city": "Winnipeg", "maintenance_pct": 10, "management_pct": 6},
]


def build() -> list[dict]:
    return [{"input": case, "output": compute(CashFlowInput(**case)).model_dump()} for case in CASES]


if __name__ == "__main__":
    FIXTURES.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {FIXTURES.relative_to(ROOT)} ({len(CASES)} cases)")
