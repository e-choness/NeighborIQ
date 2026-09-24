"""
Deterministic synthetic listing generator for demos and development.

Every listing produced here is fake and is stored with is_synthetic=1 and
source="seed"; the UI must label it as such. Neighbourhood names and centroids
are real places so the map is legible, but prices, sizes and addresses are
generated from rough per-neighbourhood $/sqft baselines and are NOT market data.

Dates are generated relative to `now`, so days-on-market stays realistic no
matter when the seed is loaded. The same `seed` value always yields the same
listings (idempotent reloads upsert by url).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class Neighbourhood:
    name: str
    region: str
    lat: float
    lon: float
    condo_ppsf: int  # rough $/sqft baseline for condos (synthetic)
    house_ppsf: int  # rough $/sqft baseline for freehold (synthetic)
    condo_share: float  # fraction of listings that are condos


@dataclass(frozen=True)
class City:
    name: str
    tax_rate: float  # approximate residential property tax rate (share of value / year)
    neighbourhoods: tuple[Neighbourhood, ...]


N = Neighbourhood
CITIES: tuple[City, ...] = (
    City("Toronto", 0.0072, (
        N("Entertainment District", "Old Toronto", 43.6465, -79.3900, 1150, 1300, 0.95),
        N("St. Lawrence", "Old Toronto", 43.6490, -79.3690, 1100, 1250, 0.85),
        N("Liberty Village", "Old Toronto", 43.6380, -79.4200, 1000, 1100, 0.90),
        N("The Annex", "Old Toronto", 43.6700, -79.4050, 1150, 1250, 0.40),
        N("Leslieville", "East York", 43.6620, -79.3320, 950, 1050, 0.30),
        N("North York Centre", "North York", 43.7680, -79.4130, 950, 900, 0.70),
        N("Scarborough Town Centre", "Scarborough", 43.7750, -79.2580, 700, 650, 0.40),
        N("Mimico", "Etobicoke", 43.6150, -79.4980, 850, 850, 0.60),
    )),
    City("Vancouver", 0.0028, (
        N("Yaletown", "Downtown", 49.2750, -123.1200, 1250, 1500, 0.95),
        N("Kitsilano", "West Side", 49.2680, -123.1650, 1200, 1400, 0.50),
        N("Mount Pleasant", "East Side", 49.2630, -123.1000, 1100, 1200, 0.55),
        N("Kerrisdale", "West Side", 49.2340, -123.1560, 1150, 1450, 0.35),
        N("Hastings-Sunrise", "East Side", 49.2780, -123.0440, 950, 1050, 0.35),
        N("Marpole", "South Vancouver", 49.2100, -123.1300, 900, 1100, 0.50),
    )),
    City("Calgary", 0.0063, (
        N("Beltline", "Centre", 51.0390, -114.0720, 430, 500, 0.95),
        N("Mission", "Centre", 51.0330, -114.0640, 450, 520, 0.70),
        N("Kensington", "Northwest", 51.0530, -114.0880, 500, 600, 0.40),
        N("Bridgeland", "Northeast", 51.0540, -114.0420, 470, 560, 0.45),
        N("Tuscany", "Northwest", 51.1250, -114.2500, 380, 390, 0.15),
        N("Mahogany", "Southeast", 50.8990, -113.9380, 400, 400, 0.20),
    )),
    City("Ottawa", 0.0108, (
        N("Centretown", "Somerset", 45.4140, -75.6950, 600, 620, 0.80),
        N("The Glebe", "Capital", 45.4020, -75.6870, 650, 700, 0.35),
        N("Westboro", "Kitchissippi", 45.3950, -75.7540, 650, 690, 0.45),
        N("Sandy Hill", "Rideau-Vanier", 45.4230, -75.6800, 580, 600, 0.60),
        N("Orléans", "Orléans", 45.4700, -75.5150, 450, 430, 0.20),
        N("Barrhaven", "Barrhaven", 45.2740, -75.7380, 440, 420, 0.15),
    )),
    City("Montreal", 0.0074, (
        N("Plateau-Mont-Royal", "Le Plateau-Mont-Royal", 45.5220, -73.5790, 700, 650, 0.60),
        N("Griffintown", "Le Sud-Ouest", 45.4930, -73.5620, 800, 700, 0.90),
        N("Rosemont", "Rosemont–La Petite-Patrie", 45.5430, -73.5850, 600, 560, 0.50),
        N("Verdun", "Verdun", 45.4580, -73.5700, 620, 560, 0.55),
        N("Villeray", "Villeray–Saint-Michel–Parc-Extension", 45.5460, -73.6230, 580, 540, 0.50),
        N("Saint-Laurent", "Saint-Laurent", 45.5050, -73.6860, 560, 520, 0.45),
    )),
)

_CONDO_BEDS = ((0, 0.08), (1, 0.40), (2, 0.42), (3, 0.10))
_CONDO_SQFT = {0: 430, 1: 600, 2: 850, 3: 1150}
_HOUSE_BEDS = ((2, 0.15), (3, 0.45), (4, 0.30), (5, 0.10))
_HOUSE_SQFT = {2: 1100, 3: 1600, 4: 2200, 5: 2900}
_FREEHOLD_TYPES = (("townhouse", 0.35), ("semi", 0.25), ("detached", 0.40))
_DECORATION = (("original", 0.25), ("standard", 0.45), ("renovated", 0.25), ("luxury", 0.05))
_DECORATION_FACTOR = {"original": 0.93, "standard": 1.0, "renovated": 1.06, "luxury": 1.15}
_TYPE_LABEL = {"condo": "Condo", "townhouse": "Townhouse", "semi": "Semi-detached", "detached": "Detached house"}


def _pick(rng: random.Random, weighted) -> object:
    values, weights = zip(*weighted)
    return rng.choices(values, weights=weights, k=1)[0]


def _asking(value: float) -> int:
    """Round like a real asking price: 849,900 rather than 851,237."""
    return max(1000, int(round(value / 1000.0)) * 1000 - 100)


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace("é", "e").replace("–", "-")


def generate_listings(
    per_neighbourhood: int = 25,
    seed: int = 42,
    now: datetime | None = None,
    cities: list[str] | None = None,
) -> list[dict]:
    """Return canonical listing dicts (see ingestion.canonical)."""
    rng = random.Random(seed)
    now = now or datetime.now(timezone.utc)
    wanted = {c.lower() for c in cities} if cities else None
    listings: list[dict] = []

    for city in CITIES:
        for hood in city.neighbourhoods:
            for i in range(per_neighbourhood):
                # Draw every random value unconditionally so filtering by city
                # never changes the listings generated for the others.
                is_condo = rng.random() < hood.condo_share
                if is_condo:
                    ptype = "condo"
                    beds = _pick(rng, _CONDO_BEDS)
                    base_sqft, ppsf = _CONDO_SQFT[beds], hood.condo_ppsf
                else:
                    ptype = _pick(rng, _FREEHOLD_TYPES)
                    beds = _pick(rng, _HOUSE_BEDS)
                    base_sqft, ppsf = _HOUSE_SQFT[beds], hood.house_ppsf
                    if ptype == "townhouse":
                        base_sqft = int(base_sqft * 0.85)

                sqft = int(base_sqft * rng.uniform(0.85, 1.18))
                age = rng.randint(1, 15) if ptype == "condo" else rng.randint(3, 90)
                decoration = _pick(rng, _DECORATION)
                noise = rng.lognormvariate(0, 0.10)
                value = sqft * ppsf * noise * _DECORATION_FACTOR[decoration] * (1 - min(age, 60) * 0.002)
                price = _asking(value)

                condo_fee = None
                if ptype == "condo" or (ptype == "townhouse" and rng.random() < 0.5):
                    condo_fee = int(sqft * rng.uniform(0.58, 0.88))
                tax = int(price * city.tax_rate * rng.uniform(0.9, 1.1))

                baths = (1.0 if beds <= 1 else 2.0) if ptype == "condo" else float(max(1, beds - 1)) + rng.choice((0.0, 0.5))
                parking = (1 if rng.random() < 0.55 else 0) if ptype == "condo" else rng.choice((1, 1, 2, 2, 3))

                days_on_market = int(rng.expovariate(1 / 28)) + 1
                listed_at = now - timedelta(days=min(days_on_market, 180), hours=rng.randint(0, 23))

                history = []
                if rng.random() < 0.3:
                    # One or two price cuts since listing — seller-motivation signal
                    cuts = 2 if (rng.random() < 0.35 and days_on_market > 30) else 1
                    original = _asking(price * (1 + rng.uniform(0.03, 0.06) * cuts))
                    history.append({"price": original, "recorded_at": listed_at.isoformat()})
                    if cuts == 2:
                        mid = _asking((original + price) / 2)
                        history.append({
                            "price": mid,
                            "recorded_at": (listed_at + timedelta(days=days_on_market // 3)).isoformat(),
                        })
                    cut_at = listed_at + timedelta(days=max(1, (days_on_market * 2) // 3))
                    history.append({"price": price, "recorded_at": cut_at.isoformat()})

                lat = hood.lat + rng.gauss(0, 0.006)
                lon = hood.lon + rng.gauss(0, 0.008)

                if wanted and city.name.lower() not in wanted:
                    continue

                beds_label = "Studio" if beds == 0 else f"{beds}-bed"
                listings.append({
                    "url": f"seed://{_slug(city.name)}/{_slug(hood.name)}/{i:03d}",
                    "title": f"{beds_label} {_TYPE_LABEL[ptype].lower()} in {hood.name}",
                    "city": city.name,
                    "region": hood.region,
                    "community": hood.name,
                    "property_type": ptype,
                    "price": price,
                    "sqft": sqft,
                    "rooms": beds,
                    "bathrooms": baths,
                    "parking": parking,
                    "age": age,
                    "decoration": decoration,
                    "condo_fee": condo_fee,
                    "property_tax": tax,
                    "status": "active",
                    "listed_at": listed_at.isoformat(),
                    "latitude": round(lat, 6),
                    "longitude": round(lon, 6),
                    "images": [],
                    "source": "seed",
                    "is_synthetic": True,
                    "price_history": history,
                })
    return listings
