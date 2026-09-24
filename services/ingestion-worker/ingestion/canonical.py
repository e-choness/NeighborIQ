"""
Canonical listing format shared by every ingestion source.

A source (seed generator, CSV/JSON import, partner feed spider) produces plain
dicts with these keys; `normalize` fills derived fields and `validate` returns a
list of problems (empty = accept). Both the CLI loaders and the Scrapy
ValidationPipeline use these functions, so every path applies the same rules.

Required: url, title, city, region, community, price
Optional: street, postal_code, property_type, sqft | area (m²), rooms (bedrooms),
          bathrooms, parking, floor, decoration, age, condo_fee (monthly),
          property_tax (annual), status, listed_at (ISO-8601), latitude,
          longitude, images, source, is_synthetic,
          price_history: [{"price": int, "recorded_at": ISO-8601}, ...]
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SQFT_PER_M2 = 10.7639

PROPERTY_TYPES = {"condo", "townhouse", "semi", "detached"}
STATUSES = {"active", "sold", "expired", "withdrawn"}

# Rough bounding box of Canada — rejects swapped lat/lon and non-Canadian points
_LAT_RANGE = (41.6, 83.2)
_LON_RANGE = (-141.1, -52.6)

MAX_PRICE = 50_000_000
SQFT_RANGE = (150, 20_000)
BEDROOM_RANGE = (0, 10)


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def normalize(item: dict) -> dict:
    """Coerce types and derive sqft ⇄ area. Returns a new dict."""
    out = dict(item)
    for key in ("price", "sqft", "rooms", "parking", "floor", "age", "condo_fee", "property_tax"):
        if key in out:
            out[key] = _to_int(out[key])
    for key in ("area", "bathrooms", "latitude", "longitude"):
        if key in out:
            out[key] = _to_float(out[key])

    sqft, area = out.get("sqft"), out.get("area")
    if sqft is None and area:
        out["sqft"] = int(round(area * SQFT_PER_M2))
    elif sqft and not area:
        out["area"] = round(sqft / SQFT_PER_M2, 2)

    for key in ("property_type", "status", "decoration"):
        if isinstance(out.get(key), str):
            out[key] = out[key].strip().lower() or None
    for key in ("city", "region", "community", "title", "street"):
        if isinstance(out.get(key), str):
            out[key] = out[key].strip()
    if isinstance(out.get("postal_code"), str):
        pc = out["postal_code"].replace(" ", "").upper()
        out["postal_code"] = f"{pc[:3]} {pc[3:]}" if len(pc) == 6 else pc or None

    out["status"] = out.get("status") or "active"
    out["listed_at"] = _to_datetime(out.get("listed_at"))
    out["is_synthetic"] = 1 if out.get("is_synthetic") else 0
    out["source"] = out.get("source") or "import"
    out["images"] = list(out.get("images") or [])
    out["price_history"] = [
        {"price": _to_int(p.get("price")), "recorded_at": _to_datetime(p.get("recorded_at"))}
        for p in (out.get("price_history") or [])
    ]
    return out


def validate(item: dict) -> list[str]:
    """Return human-readable problems for a normalized item (empty list = valid)."""
    errors: list[str] = []

    for key in ("url", "title", "city", "region", "community"):
        if not item.get(key):
            errors.append(f"missing {key}")

    price = item.get("price")
    if not price or price <= 0:
        errors.append(f"invalid price: {price!r}")
    elif price > MAX_PRICE:
        errors.append(f"price above {MAX_PRICE}: {price}")

    sqft = item.get("sqft")
    if sqft is not None and not (SQFT_RANGE[0] <= sqft <= SQFT_RANGE[1]):
        errors.append(f"sqft out of range: {sqft}")

    rooms = item.get("rooms")
    if rooms is not None and not (BEDROOM_RANGE[0] <= rooms <= BEDROOM_RANGE[1]):
        errors.append(f"bedrooms out of range: {rooms}")

    ptype = item.get("property_type")
    if ptype is not None and ptype not in PROPERTY_TYPES:
        errors.append(f"unknown property_type: {ptype!r}")

    if item.get("status") not in STATUSES:
        errors.append(f"unknown status: {item.get('status')!r}")

    lat, lon = item.get("latitude"), item.get("longitude")
    if (lat is None) != (lon is None):
        errors.append("latitude and longitude must be provided together")
    elif lat is not None and not (
        _LAT_RANGE[0] <= lat <= _LAT_RANGE[1] and _LON_RANGE[0] <= lon <= _LON_RANGE[1]
    ):
        errors.append(f"coordinates outside Canada: ({lat}, {lon})")

    for fee in ("condo_fee", "property_tax"):
        if item.get(fee) is not None and item[fee] < 0:
            errors.append(f"negative {fee}")

    return errors
