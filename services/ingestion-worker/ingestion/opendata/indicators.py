"""
Economic time series → od_indicators.

Bank of Canada Valet API (JSON): mortgage and policy rates — the cash-flow
calculator's default interest rate comes from here.
Statistics Canada full-table CSV downloads: e.g. the New Housing Price Index.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from ingestion.opendata.tabular import to_date, to_float

VALET_URL = "https://www.bankofcanada.ca/valet/observations/{series}/json?start_date={start}"

_UPSERT = text("""
    INSERT INTO od_indicators (series, date, value, label, unit, source)
    VALUES (:series, :date, :value, :label, :unit, :source)
    ON CONFLICT (series, date) DO UPDATE SET value = EXCLUDED.value, label = EXCLUDED.label
""")


def load_valet(session: Session, payload: dict, source: str = "bank_of_canada") -> int:
    """Store every series in a Valet observations response under its own id."""
    details = payload.get("seriesDetail", {})
    rows = []
    for obs in payload.get("observations", []):
        day = to_date(obs.get("d"))
        for series, cell in obs.items():
            if series == "d" or not isinstance(cell, dict):
                continue
            value = to_float(cell.get("v"))
            if day and value is not None:
                rows.append(
                    {
                        "series": f"boc:{series}",
                        "date": day,
                        "value": value,
                        "label": (details.get(series, {}).get("label") or series)[:255],
                        "unit": "percent",
                        "source": source,
                    }
                )
    if rows:
        session.execute(_UPSERT, rows)
    return len(rows)


def load_statcan_table(
    session: Session,
    fh,
    series_prefix: str,
    filters: dict[str, str],
    geo_column: str = "GEO",
    source: str = "statcan",
) -> int:
    """
    Load a StatCan full-table CSV (REF_DATE, GEO, <dimensions…>, VALUE), keeping
    rows whose dimension columns equal `filters`. One series per GEO.
    """
    reader = csv.DictReader(fh)
    rows = []
    for row in reader:
        if any(row.get(col, "").strip() != value for col, value in filters.items()):
            continue
        value = to_float(row.get("VALUE"))
        day = to_date(
            (row.get("REF_DATE") or "") + "-01" if len(row.get("REF_DATE", "")) == 7 else row.get("REF_DATE")
        )
        if value is None or day is None:
            continue
        geo = row.get(geo_column, "").split(",")[0].strip()
        rows.append(
            {
                "series": f"{series_prefix}:{geo.lower()}"[:64],
                "date": day,
                "value": value,
                "label": f"{series_prefix} — {geo}"[:255],
                "unit": row.get("UOM", "")[:32],
                "source": source,
            }
        )
        if len(rows) >= 5000:
            session.execute(_UPSERT, rows)
            rows = []
    if rows:
        session.execute(_UPSERT, rows)
    return reader.line_num - 1


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
