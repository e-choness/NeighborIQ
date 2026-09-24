"""
ListingFeedSpider — ingests a listing feed published in NeighborIQ's canonical format.

This is the pluggable source interface: any provider we have rights to use
(a brokerage's CREA DDF® export, a municipal open-data extract, a partner CSV)
is converted to canonical JSON or CSV (see ingestion/canonical.py) and served at
a URL. The spider fetches it and yields one ListingItem per row; the item
pipelines then dedup, validate, upsert (with price history) and dispatch insights.

We deliberately do not scrape MLS®/REALTOR.ca pages: their terms prohibit it.

    scrapy crawl listing_feed -a feed_url=https://partner.example/listings.json
"""
import csv
import io
import json
import logging

import scrapy
from scrapy.http import Response

from scraper.items import ListingItem

logger = logging.getLogger(__name__)


class ListingFeedSpider(scrapy.Spider):
    name = "listing_feed"

    def __init__(self, feed_url: str | None = None, source: str = "feed", *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not feed_url:
            raise ValueError("feed_url is required")
        self.feed_url = feed_url
        self.source = source

    def start_requests(self):
        yield scrapy.Request(self.feed_url, callback=self.parse, errback=self.handle_error)

    def parse(self, response: Response):
        for row in self.parse_rows(response.url, response.text):
            item = ListingItem()
            for key, value in row.items():
                if key in ListingItem.fields:
                    item[key] = value
            item.setdefault("source", self.source)
            yield item

    @staticmethod
    def parse_rows(url: str, body: str) -> list[dict]:
        """Canonical JSON (a list, or {"listings": [...]}) or CSV with a header row."""
        stripped = body.lstrip()
        if url.lower().split("?")[0].endswith(".csv") or not stripped.startswith(("[", "{")):
            return list(csv.DictReader(io.StringIO(body)))
        data = json.loads(body)
        return data["listings"] if isinstance(data, dict) else data

    def handle_error(self, failure):
        logger.error("Feed request failed: %s — %s", failure.request.url, repr(failure))
