"""Tests for the synthetic seed generator."""
from datetime import datetime, timezone

from ingestion.canonical import normalize, validate
from ingestion.seed import CITIES, generate_listings

NOW = datetime(2026, 9, 1, tzinfo=timezone.utc)


def test_deterministic():
    assert generate_listings(5, now=NOW) == generate_listings(5, now=NOW)


def test_every_listing_is_valid_and_labelled_synthetic():
    listings = generate_listings(10, now=NOW)
    assert len(listings) == 10 * sum(len(c.neighbourhoods) for c in CITIES)
    for raw in listings:
        item = normalize(raw)
        assert validate(item) == [], raw["url"]
        assert item["is_synthetic"] == 1
        assert item["source"] == "seed"
        assert item["url"].startswith("seed://")


def test_urls_unique():
    listings = generate_listings(25, now=NOW)
    assert len({l["url"] for l in listings}) == len(listings)


def test_city_filter_does_not_change_other_listings():
    all_listings = {l["url"]: l for l in generate_listings(5, now=NOW)}
    calgary = generate_listings(5, now=NOW, cities=["calgary"])
    assert calgary and all(l["city"] == "Calgary" for l in calgary)
    assert all(all_listings[l["url"]] == l for l in calgary)


def test_price_history_ends_at_current_price():
    for listing in generate_listings(25, now=NOW):
        history = listing["price_history"]
        if history:
            assert history[-1]["price"] == listing["price"]
            assert history[0]["price"] > listing["price"]  # cuts only


def test_condos_carry_fees_and_everyone_pays_tax():
    for listing in generate_listings(10, now=NOW):
        assert listing["property_tax"] > 0
        if listing["property_type"] == "condo":
            assert listing["condo_fee"] > 0
