"""
Tests for ValidationPipeline.

Covers all validation rules:
  - price > 0
  - community non-empty
  - rooms in [1, 10]
  - area in [10, 500] m²
"""
import pytest
from scrapy.exceptions import DropItem

from scraper.items import HouseItem
from scraper.pipelines.validation import ValidationPipeline


def _make_valid_item(**overrides):
    item = HouseItem(
        url="http://nanjing.lianjia.com/ershoufang/101000000000001.html",
        title="Test House",
        community="Test Community",
        city="nanjing",
        region="gulou",
        street="zhongshan",
        price=2000000,
        area=90.0,
        rooms=3,
        floor=5,
        decoration="精装",
        age=10,
    )
    for k, v in overrides.items():
        item[k] = v
    return item


class TestValidationPipeline:
    def _pipeline(self):
        return ValidationPipeline()

    # ---- Valid item --------------------------------------------------------

    def test_valid_item_passes(self):
        item = _make_valid_item()
        result = self._pipeline().process_item(item, spider=None)
        assert result["price"] == 2000000

    # ---- Price validation --------------------------------------------------

    def test_price_zero_dropped(self):
        item = _make_valid_item(price=0)
        with pytest.raises(DropItem, match="invalid price"):
            self._pipeline().process_item(item, spider=None)

    def test_price_negative_dropped(self):
        item = _make_valid_item(price=-100)
        with pytest.raises(DropItem, match="invalid price"):
            self._pipeline().process_item(item, spider=None)

    def test_price_none_dropped(self):
        item = _make_valid_item(price=None)
        with pytest.raises(DropItem, match="invalid price"):
            self._pipeline().process_item(item, spider=None)

    def test_price_as_string_coerced(self):
        item = _make_valid_item(price="1500000")
        result = self._pipeline().process_item(item, spider=None)
        assert result["price"] == 1500000

    # ---- Community validation ----------------------------------------------

    def test_empty_community_dropped(self):
        item = _make_valid_item(community="")
        with pytest.raises(DropItem, match="missing community"):
            self._pipeline().process_item(item, spider=None)

    def test_whitespace_community_dropped(self):
        item = _make_valid_item(community="   ")
        with pytest.raises(DropItem, match="missing community"):
            self._pipeline().process_item(item, spider=None)

    def test_none_community_dropped(self):
        item = _make_valid_item(community=None)
        with pytest.raises(DropItem, match="missing community"):
            self._pipeline().process_item(item, spider=None)

    # ---- Rooms validation --------------------------------------------------

    def test_rooms_0_dropped(self):
        item = _make_valid_item(rooms=0)
        with pytest.raises(DropItem, match="rooms out of range"):
            self._pipeline().process_item(item, spider=None)

    def test_rooms_11_dropped(self):
        item = _make_valid_item(rooms=11)
        with pytest.raises(DropItem, match="rooms out of range"):
            self._pipeline().process_item(item, spider=None)

    def test_rooms_1_passes(self):
        item = _make_valid_item(rooms=1)
        result = self._pipeline().process_item(item, spider=None)
        assert result["rooms"] == 1

    def test_rooms_10_passes(self):
        item = _make_valid_item(rooms=10)
        result = self._pipeline().process_item(item, spider=None)
        assert result["rooms"] == 10

    def test_rooms_none_passes(self):
        # None rooms are allowed (field is optional)
        item = _make_valid_item(rooms=None)
        result = self._pipeline().process_item(item, spider=None)
        assert result is not None

    # ---- Area validation ---------------------------------------------------

    def test_area_too_small_dropped(self):
        item = _make_valid_item(area=5.0)
        with pytest.raises(DropItem, match="area out of range"):
            self._pipeline().process_item(item, spider=None)

    def test_area_too_large_dropped(self):
        item = _make_valid_item(area=600.0)
        with pytest.raises(DropItem, match="area out of range"):
            self._pipeline().process_item(item, spider=None)

    def test_area_boundary_10_passes(self):
        item = _make_valid_item(area=10.0)
        result = self._pipeline().process_item(item, spider=None)
        assert result["area"] == 10.0

    def test_area_boundary_500_passes(self):
        item = _make_valid_item(area=500.0)
        result = self._pipeline().process_item(item, spider=None)
        assert result["area"] == 500.0

    def test_area_none_passes(self):
        item = _make_valid_item(area=None)
        result = self._pipeline().process_item(item, spider=None)
        assert result is not None
