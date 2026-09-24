"""
Tests for ValidationPipeline — the shared canonical listing rules applied to Scrapy items.
"""

import pytest
from scrapy.exceptions import DropItem

from scraper.items import ListingItem
from scraper.pipelines.validation import ValidationPipeline


def _item(**overrides) -> ListingItem:
    base = dict(
        url="https://feeds.partner.example/listing/1",
        title="2-bed condo in Liberty Village",
        city="Toronto",
        region="Old Toronto",
        community="Liberty Village",
        property_type="condo",
        price=749900,
        sqft=820,
        rooms=2,
        latitude=43.638,
        longitude=-79.42,
    )
    base.update(overrides)
    return ListingItem(**base)


@pytest.fixture()
def pipeline():
    return ValidationPipeline()


def test_valid_item_passes_and_derives_area(pipeline):
    result = pipeline.process_item(_item(), spider=None)
    assert result["area"] == pytest.approx(76.18, abs=0.01)
    assert result["status"] == "active"


def test_price_as_string_coerced(pipeline):
    assert pipeline.process_item(_item(price="749900"), spider=None)["price"] == 749900


@pytest.mark.parametrize("price", [0, -1, None, "abc", 60_000_000])
def test_invalid_price_dropped(pipeline, price):
    with pytest.raises(DropItem, match="price"):
        pipeline.process_item(_item(price=price), spider=None)


@pytest.mark.parametrize("field", ["community", "city", "region", "title", "url"])
def test_missing_required_field_dropped(pipeline, field):
    with pytest.raises(DropItem, match=f"missing {field}"):
        pipeline.process_item(_item(**{field: "  " if field != "url" else None}), spider=None)


def test_bachelor_unit_allowed(pipeline):
    """0 bedrooms is a studio/bachelor — common in Canadian condo stock."""
    assert pipeline.process_item(_item(rooms=0), spider=None)["rooms"] == 0


@pytest.mark.parametrize("rooms", [-1, 11])
def test_bedrooms_out_of_range_dropped(pipeline, rooms):
    with pytest.raises(DropItem, match="bedrooms"):
        pipeline.process_item(_item(rooms=rooms), spider=None)


@pytest.mark.parametrize("sqft", [100, 25_000])
def test_sqft_out_of_range_dropped(pipeline, sqft):
    with pytest.raises(DropItem, match="sqft"):
        pipeline.process_item(_item(sqft=sqft), spider=None)


def test_area_only_derives_sqft(pipeline):
    result = pipeline.process_item(_item(sqft=None, area=100), spider=None)
    assert result["sqft"] == 1076


def test_unknown_property_type_dropped(pipeline):
    with pytest.raises(DropItem, match="property_type"):
        pipeline.process_item(_item(property_type="castle"), spider=None)


def test_coordinates_outside_canada_dropped(pipeline):
    with pytest.raises(DropItem, match="outside Canada"):
        pipeline.process_item(_item(latitude=32.06, longitude=118.79), spider=None)


def test_swapped_coordinates_dropped(pipeline):
    with pytest.raises(DropItem, match="outside Canada"):
        pipeline.process_item(_item(latitude=-79.42, longitude=43.638), spider=None)


def test_half_coordinates_dropped(pipeline):
    with pytest.raises(DropItem, match="together"):
        pipeline.process_item(_item(longitude=None), spider=None)


def test_postal_code_normalized(pipeline):
    assert pipeline.process_item(_item(postal_code="m5v2t6"), spider=None)["postal_code"] == "M5V 2T6"
