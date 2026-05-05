"""
Tests for CoordinateConversionPipeline (pass-through).

Canadian real estate data is already in WGS-84, so the pipeline is a no-op.
All items pass through with coordinates unchanged.
"""
from scraper.items import HouseItem
from scraper.pipelines.coordinate import CoordinateConversionPipeline


class TestCoordinateConversionPipeline:
    def _pipeline(self):
        return CoordinateConversionPipeline()

    def test_coordinates_unchanged_for_toronto(self):
        pipeline = self._pipeline()
        item = HouseItem(latitude=43.6532, longitude=-79.3832)
        result = pipeline.process_item(item, spider=None)
        assert result["latitude"] == 43.6532
        assert result["longitude"] == -79.3832

    def test_coordinates_unchanged_for_vancouver(self):
        pipeline = self._pipeline()
        item = HouseItem(latitude=49.2827, longitude=-123.1207)
        result = pipeline.process_item(item, spider=None)
        assert result["latitude"] == 49.2827
        assert result["longitude"] == -123.1207

    def test_none_coordinates_pass_through(self):
        pipeline = self._pipeline()
        item = HouseItem(latitude=None, longitude=None)
        result = pipeline.process_item(item, spider=None)
        assert result["latitude"] is None
        assert result["longitude"] is None

    def test_missing_coordinates_pass_through(self):
        pipeline = self._pipeline()
        item = HouseItem(url="http://example.com/listing/1")
        result = pipeline.process_item(item, spider=None)
        assert result is item  # same object, unchanged

    def test_item_returned_unchanged(self):
        pipeline = self._pipeline()
        item = HouseItem(
            url="http://example.com/listing/2",
            latitude=45.4215,
            longitude=-75.6972,
            price=650000,
        )
        result = pipeline.process_item(item, spider=None)
        assert result["latitude"] == 45.4215
        assert result["longitude"] == -75.6972
        assert result["price"] == 650000
