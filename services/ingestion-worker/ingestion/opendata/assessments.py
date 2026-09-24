"""
Municipal assessment rolls → od_properties.

These are the only open, property-level valuation data in Canada: every taxed
property with its assessed value, and depending on the city, year built, lot
size, zoning and tax levy. They power the "analyse any address" flow and give
comps a second, assessment-based reference alongside asking prices.

Coverage: Vancouver, Calgary, Edmonton, Montréal publish rolls; Toronto and
Ottawa (MPAC) and the rest of Ontario do not.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from ingestion.opendata.areas import normalize_area_name
from ingestion.opendata.tabular import apply_geo_point, rows, to_float, to_int

REQUIRED = ("source_id",)

_UPSERT = text("""
    INSERT INTO od_properties
        (city, source, source_id, address, postal_code, latitude, longitude, neighbourhood,
         property_class, zoning, year_built, units, floor_area_sqft, lot_size_sqft,
         land_value, improvement_value, assessed_value, previous_value, tax_levy, assessment_year)
    VALUES
        (:city, :source, :source_id, :address, :postal_code, :latitude, :longitude, :neighbourhood,
         :property_class, :zoning, :year_built, :units, :floor_area_sqft, :lot_size_sqft,
         :land_value, :improvement_value, :assessed_value, :previous_value, :tax_levy, :assessment_year)
    ON CONFLICT (source, source_id) DO UPDATE SET
        address = EXCLUDED.address, postal_code = EXCLUDED.postal_code,
        latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude,
        neighbourhood = EXCLUDED.neighbourhood, property_class = EXCLUDED.property_class,
        zoning = EXCLUDED.zoning, year_built = EXCLUDED.year_built, units = EXCLUDED.units,
        floor_area_sqft = EXCLUDED.floor_area_sqft, lot_size_sqft = EXCLUDED.lot_size_sqft,
        land_value = EXCLUDED.land_value, improvement_value = EXCLUDED.improvement_value,
        assessed_value = EXCLUDED.assessed_value, previous_value = EXCLUDED.previous_value,
        tax_levy = EXCLUDED.tax_levy, assessment_year = EXCLUDED.assessment_year, loaded_at = now()
    -- Exports can hold several roll years per property: never overwrite newer with older
    WHERE od_properties.assessment_year IS NULL
       OR EXCLUDED.assessment_year IS NULL
       OR EXCLUDED.assessment_year >= od_properties.assessment_year
""")

SQM_TO_SQFT = 10.7639


def normalize(raw: dict, city: str, source: str, options: dict) -> dict | None:
    if not raw.get("source_id"):
        return None
    apply_geo_point(raw)
    address = raw.get("address") or " ".join(
        p for p in (raw.get("civic_number"), raw.get("street_name")) if p
    ) or None
    land, improvement = to_int(raw.get("land_value")), to_int(raw.get("improvement_value"))
    assessed = to_int(raw.get("assessed_value"))
    if assessed is None and (land is not None or improvement is not None):
        assessed = (land or 0) + (improvement or 0)
    area_factor = SQM_TO_SQFT if options.get("areas_in_sqm") else 1.0
    floor = to_float(raw.get("floor_area"))
    lot = to_float(raw.get("lot_size"))
    lat, lon = to_float(raw.get("latitude")), to_float(raw.get("longitude"))
    if lat is not None and not (41 < lat < 84 and -142 < (lon or 0) < -52):
        lat = lon = None  # projected coordinates or junk; area falls back to neighbourhood name
    postal = (raw.get("postal_code") or "").replace(" ", "").upper()
    return {
        "city": city,
        "source": source,
        "source_id": raw["source_id"][:64],
        "address": address[:255] if address else None,
        "postal_code": f"{postal[:3]} {postal[3:]}" if len(postal) == 6 else None,
        "latitude": lat,
        "longitude": lon,
        "neighbourhood": normalize_area_name(raw.get("neighbourhood")),
        "property_class": (raw.get("property_class") or None),
        "zoning": (raw.get("zoning") or None),
        "year_built": to_int(raw.get("year_built")) or None,
        "units": to_int(raw.get("units")),
        "floor_area_sqft": int(floor * area_factor) if floor else None,
        "lot_size_sqft": int(lot * area_factor) if lot else None,
        "land_value": land,
        "improvement_value": improvement,
        "assessed_value": assessed,
        "previous_value": to_int(raw.get("previous_value")),
        "tax_levy": to_int(raw.get("tax_levy")),
        "assessment_year": to_int(raw.get("assessment_year")),
    }


def load(session: Session, fh, city: str, source: str, mapping: dict, options: dict | None = None,
         batch_size: int = 2000) -> int:
    options = options or {}
    wanted = options.get("filter")  # optional {field: allowed values}
    batch, total = [], 0
    for raw in rows(fh, mapping, REQUIRED):
        if wanted and any(raw.get(k, "").upper() not in v for k, v in wanted.items()):
            continue
        record = normalize(raw, city, source, options)
        if record:
            batch.append(record)
        if len(batch) >= batch_size:
            session.execute(_UPSERT, batch)
            total += len(batch)
            batch = []
    if batch:
        session.execute(_UPSERT, batch)
        total += len(batch)
    return total
