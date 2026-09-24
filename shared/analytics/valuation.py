"""
Comparable-listing valuation and rent estimates.

Fair value = median $/sqft of nearby comparable listings × subject sqft.
The comps are returned with the answer so the user can see (and disagree with)
the evidence. Comps are *active asking prices*, not sold prices — sold data in
Canada is board-licensed — so the result reads "vs. comparable asking prices".
"""
from __future__ import annotations

import math
import statistics
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

METHOD = "comps-v1"

# Search rings: widen until enough comps are found
RADII_M = (1500, 3000, 6000)
MIN_COMPS = 4
MAX_COMPS = 8
SQFT_TOLERANCE = 0.35  # ±35% size band
IN_LINE_BAND_PCT = 5.0

RENT_NOTE = (
    "City average rent for this bedroom count (CMHC Rental Market Survey format). "
    "Averages include long-standing tenancies, so asking rent for a vacant unit is "
    "usually higher — replace it with your own estimate."
)


class Comp(BaseModel):
    house_id: int
    title: str
    community: Optional[str]
    price: int
    sqft: int
    rooms: Optional[int]
    price_per_sqft: float
    distance_m: int
    latitude: float
    longitude: float


class Valuation(BaseModel):
    method: str = METHOD
    basis: str = "active asking prices"
    asking_price: int
    fair_value: int
    fair_value_low: int
    fair_value_high: int
    median_price_per_sqft: float
    subject_price_per_sqft: float
    delta_pct: float  # (asking − fair) / fair × 100; negative = priced below comps
    verdict: str  # below | in_line | above
    confidence: str  # high | medium | low
    radius_m: int
    comps: list[Comp]


class RentEstimate(BaseModel):
    monthly_rent: int
    bedrooms: int
    city: str
    source: str
    survey_date: Optional[str]
    note: str = RENT_NOTE


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def select_comps(subject: dict, candidates: list[dict]) -> tuple[list[Comp], int]:
    """Nearest comparable candidates, widening the radius until MIN_COMPS are found."""
    lat, lon = float(subject["latitude"]), float(subject["longitude"])
    scored = []
    for c in candidates:
        d = haversine_m(lat, lon, float(c["latitude"]), float(c["longitude"]))
        scored.append((d, c))
    scored.sort(key=lambda x: x[0])

    chosen, radius = [], RADII_M[-1]
    for radius in RADII_M:
        chosen = [(d, c) for d, c in scored if d <= radius][:MAX_COMPS]
        if len(chosen) >= MIN_COMPS:
            break

    comps = [
        Comp(
            house_id=c["id"],
            title=c["title"],
            community=c.get("community"),
            price=int(c["price"]),
            sqft=int(c["sqft"]),
            rooms=c.get("rooms"),
            price_per_sqft=round(c["price"] / c["sqft"], 2),
            distance_m=int(round(d)),
            latitude=float(c["latitude"]),
            longitude=float(c["longitude"]),
        )
        for d, c in chosen
    ]
    return comps, radius


def value_from_comps(subject: dict, comps: list[Comp], radius_m: int) -> Optional[Valuation]:
    """Median-$/sqft valuation. None when there is not enough evidence to say anything."""
    if len(comps) < 2 or not subject.get("sqft"):
        return None
    sqft, asking = int(subject["sqft"]), int(subject["price"])
    ppsf = [c.price_per_sqft for c in comps]
    median = statistics.median(ppsf)
    q1, q3 = _quantile(ppsf, 0.25), _quantile(ppsf, 0.75)
    fair = median * sqft
    delta = (asking - fair) / fair * 100
    dispersion = (q3 - q1) / median if median else 1.0

    if len(comps) >= 6 and dispersion < 0.15:
        confidence = "high"
    elif len(comps) >= MIN_COMPS and dispersion < 0.25:
        confidence = "medium"
    else:
        confidence = "low"

    verdict = "in_line"
    if delta < -IN_LINE_BAND_PCT:
        verdict = "below"
    elif delta > IN_LINE_BAND_PCT:
        verdict = "above"

    return Valuation(
        asking_price=asking,
        fair_value=int(round(fair, -3)),
        fair_value_low=int(round(q1 * sqft, -3)),
        fair_value_high=int(round(q3 * sqft, -3)),
        median_price_per_sqft=round(median, 2),
        subject_price_per_sqft=round(asking / sqft, 2),
        delta_pct=round(delta, 1),
        verdict=verdict,
        confidence=confidence,
        radius_m=radius_m,
        comps=comps,
    )


# ---------------------------------------------------------------------------
# DB access
# ---------------------------------------------------------------------------

_SUBJECT_SQL = text("""
    SELECT id, title, city, region, community, property_type, price, sqft, rooms,
           bathrooms, age, condo_fee, property_tax, latitude, longitude, is_synthetic, area_id
    FROM house_houses WHERE id = :id
""")

# Same city and property type, similar size and bedroom count, within a bounding box
# of the widest search ring; exact distance is computed in Python.
_CANDIDATES_SQL = text("""
    SELECT id, title, community, price, sqft, rooms, latitude, longitude
    FROM house_houses
    WHERE is_active = 1
      AND id <> :id
      AND LOWER(city) = LOWER(:city)
      AND property_type IS NOT DISTINCT FROM :property_type
      AND sqft BETWEEN :sqft_lo AND :sqft_hi
      AND (CAST(:rooms AS INTEGER) IS NULL OR rooms BETWEEN :rooms - 1 AND :rooms + 1)
      AND latitude BETWEEN :lat_lo AND :lat_hi
      AND longitude BETWEEN :lon_lo AND :lon_hi
""")


def fetch_subject(db: Session, house_id: int) -> Optional[dict]:
    row = db.execute(_SUBJECT_SQL, {"id": house_id}).mappings().fetchone()
    return dict(row) if row else None


def valuation_for(db: Session, subject: dict) -> Optional[Valuation]:
    if subject.get("latitude") is None or not subject.get("sqft"):
        return None
    lat, lon, sqft = float(subject["latitude"]), float(subject["longitude"]), int(subject["sqft"])
    reach = RADII_M[-1]
    dlat = reach / 111_000
    dlon = reach / (111_000 * max(math.cos(math.radians(lat)), 0.01))
    rows = db.execute(_CANDIDATES_SQL, {
        "id": subject["id"],
        "city": subject["city"],
        "property_type": subject.get("property_type"),
        "sqft_lo": int(sqft * (1 - SQFT_TOLERANCE)),
        "sqft_hi": int(sqft * (1 + SQFT_TOLERANCE)),
        "rooms": subject.get("rooms"),
        "lat_lo": lat - dlat, "lat_hi": lat + dlat,
        "lon_lo": lon - dlon, "lon_hi": lon + dlon,
    }).mappings().all()
    comps, radius = select_comps(subject, [dict(r) for r in rows])
    return value_from_comps(subject, comps, radius)


def rent_estimate_for(db: Session, city: str, bedrooms: Optional[int]) -> Optional[RentEstimate]:
    beds = min(max(bedrooms or 0, 0), 3)
    row = db.execute(
        text("""
            SELECT avg_rent, source, survey_date FROM house_rent_benchmarks
            WHERE LOWER(city) = LOWER(:city) AND bedrooms = :beds
        """),
        {"city": city, "beds": beds},
    ).fetchone()
    if row is None:
        return None
    return RentEstimate(
        monthly_rent=int(row.avg_rent), bedrooms=beds, city=city,
        source=row.source, survey_date=row.survey_date,
    )
