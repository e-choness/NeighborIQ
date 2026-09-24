"""
Rent benchmark loader.

Reads a CSV with columns city,bedrooms,avg_rent,source,survey_date and upserts
house_rent_benchmarks. The format mirrors CMHC Rental Market Survey tables
(average rent by bedroom type per CMA) so the official export can be dropped in
after light reshaping. bedrooms: 0 = bachelor, 3 = three bedrooms or more.
"""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

REQUIRED = ("city", "bedrooms", "avg_rent", "source")


def read_csv(path: str | Path) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(line for line in fh if not line.startswith("#"))
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing columns {missing}")
        for row in reader:
            rows.append(
                {
                    "city": row["city"].strip(),
                    "bedrooms": int(row["bedrooms"]),
                    "avg_rent": int(row["avg_rent"]),
                    "source": row["source"].strip(),
                    "survey_date": (row.get("survey_date") or "").strip() or None,
                }
            )
    return rows


def load(session: Session, rows: list[dict]) -> int:
    for row in rows:
        session.execute(
            text("""
                INSERT INTO house_rent_benchmarks (city, bedrooms, avg_rent, source, survey_date)
                VALUES (:city, :bedrooms, :avg_rent, :source, :survey_date)
                ON CONFLICT (city, bedrooms) DO UPDATE SET
                    avg_rent = EXCLUDED.avg_rent,
                    source = EXCLUDED.source,
                    survey_date = EXCLUDED.survey_date
            """),
            row,
        )
    return len(rows)
