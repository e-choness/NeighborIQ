"""Tests for ListingFeedSpider — canonical JSON / CSV feeds, no network."""
import json

import pytest
from scrapy.http import Request, TextResponse

from scraper.items import ListingItem
from scraper.spiders.feed_spider import ListingFeedSpider

ROW = {
    "url": "https://feeds.partner.example/listing/1",
    "title": "3-bed semi in Leslieville",
    "city": "Toronto",
    "region": "East York",
    "community": "Leslieville",
    "property_type": "semi",
    "price": 1349000,
    "sqft": 1650,
    "rooms": 3,
    "unknown_column": "ignored",
}


def _response(url: str, body: str) -> TextResponse:
    return TextResponse(url=url, body=body.encode(), encoding="utf-8", request=Request(url))


def test_requires_feed_url():
    with pytest.raises(ValueError):
        ListingFeedSpider()


def test_start_request_targets_feed():
    spider = ListingFeedSpider(feed_url="https://feeds.partner.example/l.json")
    assert [r.url for r in spider.start_requests()] == ["https://feeds.partner.example/l.json"]


def test_parses_json_list():
    spider = ListingFeedSpider(feed_url="https://x.example/l.json", source="partner")
    items = list(spider.parse(_response("https://x.example/l.json", json.dumps([ROW]))))
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, ListingItem)
    assert item["price"] == 1349000
    assert item["source"] == "partner"
    assert "unknown_column" not in item


def test_parses_json_envelope():
    spider = ListingFeedSpider(feed_url="https://x.example/l.json")
    body = json.dumps({"listings": [ROW, ROW]})
    assert len(list(spider.parse(_response("https://x.example/l.json", body)))) == 2


def test_parses_csv():
    spider = ListingFeedSpider(feed_url="https://x.example/l.csv")
    header = "url,title,city,region,community,price,sqft,rooms"
    body = f"{header}\nhttps://x.example/2,Condo,Calgary,Centre,Beltline,389900,700,1\n"
    items = list(spider.parse(_response("https://x.example/l.csv", body)))
    assert items[0]["community"] == "Beltline"
    assert items[0]["price"] == "389900"  # coerced later by ValidationPipeline
