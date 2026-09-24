"""The docs' JavaScript calculator is checked against these fixtures; keep them true to the Python."""

import json
import math
from pathlib import Path

import pytest

from shared.analytics.cashflow import CashFlowInput, compute

FIXTURES = (
    Path(__file__).resolve().parents[2] / "docs" / ".vitepress" / "theme" / "lib" / "cashflow.fixtures.json"
)
CASES = json.loads(FIXTURES.read_text())


def _close(a, b) -> bool:
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k]) for k in a)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, abs_tol=0.011)
    return a == b


@pytest.mark.parametrize("case", CASES, ids=[f"{c['input']['city']}-{c['input']['price']}" for c in CASES])
def test_python_matches_fixture(case):
    actual = compute(CashFlowInput(**case["input"])).model_dump()
    drifted = [k for k in case["output"] if not _close(actual[k], case["output"][k])]
    assert not drifted, f"cash-flow output changed for {drifted}; run scripts/export_cashflow_fixtures.py"
