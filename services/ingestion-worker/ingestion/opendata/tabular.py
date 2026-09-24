"""
Column mapping for tabular open data.

A mapping is {canonical_field: [candidate column names]}; the first candidate
present in the file wins (case-insensitive). Portals rename columns between
releases, so listing alternatives keeps loaders working, and a missing
required field fails loudly with the columns that *are* available.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterable, Iterator
from datetime import date, datetime


class SchemaError(ValueError):
    pass


def resolve(header: list[str], mapping: dict[str, list[str]], required: Iterable[str]) -> dict[str, str]:
    lower = {h.strip().lower(): h for h in header}
    resolved = {}
    for field, candidates in mapping.items():
        for candidate in candidates:
            if candidate.lower() in lower:
                resolved[field] = lower[candidate.lower()]
                break
    missing = [f for f in required if f not in resolved]
    if missing:
        raise SchemaError(
            f"Missing required columns for {missing} (tried {[mapping[f] for f in missing]}); "
            f"file has: {header[:40]}"
        )
    return resolved


def rows(fh, mapping: dict[str, list[str]], required: Iterable[str]) -> Iterator[dict]:
    """Yield {canonical_field: raw string} for each CSV row."""
    reader = csv.DictReader(fh)
    columns = resolve(reader.fieldnames or [], mapping, required)
    for row in reader:
        yield {field: (row.get(column) or "").strip() for field, column in columns.items()}


_NUMBER = re.compile(r"[^0-9.\-]")


def to_float(value) -> float | None:
    """Parse numbers like "1,234,000", "$850.5" or 12; None when empty or unparseable."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(_NUMBER.sub("", str(value)))
    except ValueError:
        return None


def to_int(value) -> int | None:
    number = to_float(value)
    return int(round(number)) if number is not None else None


_DATE_FORMATS = (("%Y-%m-%d", 10), ("%Y/%m/%d", 10), ("%m/%d/%Y", 10), ("%Y%m%d", 8))


def to_date(value) -> date | None:
    """First 10 characters as a date in a common portal format (ISO timestamps included)."""
    text = str(value or "").strip()
    for fmt, length in _DATE_FORMATS:
        try:
            return datetime.strptime(text[:length], fmt).date()
        except ValueError:
            continue
    return None


def apply_geo_point(raw: dict) -> dict:
    """Opendatasoft exports coordinates as one "lat, lon" column (geo_point_2d)."""
    point = raw.pop("geo_point", "")
    if point and not raw.get("latitude"):
        parts = [p.strip() for p in point.replace(";", ",").split(",")]
        if len(parts) == 2:
            raw["latitude"], raw["longitude"] = parts
    return raw


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:48]
