"""
Tests for RedisDedupPipeline.

Uses unittest.mock to avoid requiring a live Redis connection.
"""
from unittest.mock import MagicMock, patch

import pytest
from scrapy.exceptions import DropItem

from scraper.items import HouseItem
from scraper.pipelines.dedup import RedisDedupPipeline


def _make_pipeline(seen_urls=None):
    """Return a pipeline with a mocked Redis client."""
    pipeline = RedisDedupPipeline(
        redis_url="redis://localhost:6379/0",
        ttl_seconds=604800,
    )
    mock_client = MagicMock()
    # If url is in seen_urls, pretend the key exists
    seen_urls = seen_urls or []

    def exists_side_effect(key):
        # Pretend the (url, price=None, status=active) fingerprint was seen
        return any(key == pipeline._make_key(url) for url in seen_urls)

    mock_client.exists.side_effect = exists_side_effect
    pipeline.client = mock_client
    return pipeline, mock_client


class TestRedisDedupPipeline:
    def test_new_url_passes_through(self):
        pipeline, mock_client = _make_pipeline()
        item = HouseItem(url="https://feeds.partner.example/listing/101.html")
        result = pipeline.process_item(item, spider=None)
        assert result == item
        mock_client.setex.assert_called_once()

    def test_seen_url_is_dropped(self):
        url = "https://feeds.partner.example/listing/101.html"
        pipeline, _ = _make_pipeline(seen_urls=[url])
        item = HouseItem(url=url)
        with pytest.raises(DropItem, match="Unchanged listing"):
            pipeline.process_item(item, spider=None)

    def test_different_url_passes(self):
        url1 = "https://feeds.partner.example/listing/101.html"
        url2 = "https://feeds.partner.example/listing/102.html"
        pipeline, mock_client = _make_pipeline(seen_urls=[url1])
        item = HouseItem(url=url2)
        result = pipeline.process_item(item, spider=None)
        assert result == item

    def test_item_without_url_passes_through(self):
        pipeline, mock_client = _make_pipeline()
        item = HouseItem(title="No URL item")
        result = pipeline.process_item(item, spider=None)
        assert result == item
        # Should not call exists or setex
        mock_client.exists.assert_not_called()
        mock_client.setex.assert_not_called()

    def test_ttl_is_set_on_new_url(self):
        pipeline, mock_client = _make_pipeline()
        ttl = 604800  # 7 days
        pipeline.ttl_seconds = ttl
        item = HouseItem(url="http://example.com/house/999.html")
        pipeline.process_item(item, spider=None)
        # setex should be called with our TTL
        call_args = mock_client.setex.call_args
        assert call_args[0][1] == ttl

    def test_key_uses_sha256_prefix(self):
        import hashlib
        pipeline, mock_client = _make_pipeline()
        url = "https://feeds.partner.example/listing/xyz.html"
        item = HouseItem(url=url)
        pipeline.process_item(item, spider=None)
        # Fingerprint is url|price|status (price absent → "None", status defaults to active)
        url_hash = hashlib.sha256(f"{url}|None|active".encode()).hexdigest()
        expected_key = f"scraper:dedup:{url_hash}"
        mock_client.exists.assert_called_with(expected_key)


class TestPriceChangeFingerprint:
    def test_price_change_passes_through(self):
        """A re-listed home at a new price must reach the writer (price history)."""
        url = "https://feeds.partner.example/listing/7"
        pipeline, _ = _make_pipeline()
        seen = {pipeline._make_key(url, 900000, "active")}
        pipeline.client.exists.side_effect = lambda key: key in seen

        with pytest.raises(DropItem):
            pipeline.process_item(HouseItem(url=url, price=900000, status="active"), spider=None)
        result = pipeline.process_item(HouseItem(url=url, price=875000, status="active"), spider=None)
        assert result["price"] == 875000

    def test_status_change_passes_through(self):
        url = "https://feeds.partner.example/listing/8"
        pipeline, _ = _make_pipeline()
        seen = {pipeline._make_key(url, 900000, "active")}
        pipeline.client.exists.side_effect = lambda key: key in seen
        result = pipeline.process_item(HouseItem(url=url, price=900000, status="sold"), spider=None)
        assert result["status"] == "sold"
