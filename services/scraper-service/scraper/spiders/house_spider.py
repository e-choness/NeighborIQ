"""
HouseSpider — House listing spider.

Parses house listings for one or more cities.
Handles multi-page pagination automatically.

Spider hierarchy as specified in Phase 4A:
  CitySpider → RegionSpider → StreetSpider → HouseSpider

This module implements all four levels. The single `LianjiaHouseSpider`
class handles the full hierarchy via chained request callbacks.
"""
import re
import logging

import scrapy
from scrapy.http import Response

from scraper.items import HouseItem

logger = logging.getLogger(__name__)

DEFAULT_CITIES = ["toronto", "vancouver", "calgary", "ottawa", "montreal"]


class LianjiaHouseSpider(scrapy.Spider):
    name = "lianjia_houses"
    allowed_domains = ["lianjia.com"]

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
    }

    def __init__(self, cities=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if cities:
            self.cities = cities.split(",") if isinstance(cities, str) else list(cities)
        else:
            self.cities = DEFAULT_CITIES

    def start_requests(self):
        """Entry point: one request per city listing page."""
        for city in self.cities:
            url = f"https://{city}.lianjia.com/ershoufang/"
            yield scrapy.Request(
                url,
                callback=self.parse_city,
                cb_kwargs={"city": city},
                errback=self.handle_error,
            )

    # ------------------------------------------------------------------ #
    # City level — parse region links
    # ------------------------------------------------------------------ #
    def parse_city(self, response: Response, city: str):
        """Extract region (district) links from the city listing page."""
        region_links = response.css("div.areaList a[href*='/ershoufang/']::attr(href)").getall()

        if not region_links:
            # Fallback: scrape the city-level listing directly
            logger.info("No region links found for %s, parsing city page directly", city)
            yield from self.parse_listings(response, city=city, region="")
            return

        for href in region_links:
            region = href.strip("/").split("/")[-1]
            if not region or region == "ershoufang":
                continue
            url = response.urljoin(href)
            yield scrapy.Request(
                url,
                callback=self.parse_region,
                cb_kwargs={"city": city, "region": region},
                errback=self.handle_error,
            )

    # ------------------------------------------------------------------ #
    # Region level — parse street / district sub-area links
    # ------------------------------------------------------------------ #
    def parse_region(self, response: Response, city: str, region: str):
        """Extract street-level sub-region links, or fall back to listing parse."""
        street_links = response.css("div.areaList a[href*='/ershoufang/']::attr(href)").getall()

        if not street_links:
            yield from self.parse_listings(response, city=city, region=region, street="")
            return

        for href in street_links:
            street = href.strip("/").split("/")[-1]
            if not street or street == region:
                continue
            url = response.urljoin(href)
            yield scrapy.Request(
                url,
                callback=self.parse_street,
                cb_kwargs={"city": city, "region": region, "street": street},
                errback=self.handle_error,
            )

    # ------------------------------------------------------------------ #
    # Street level — parse listings
    # ------------------------------------------------------------------ #
    def parse_street(self, response: Response, city: str, region: str, street: str):
        yield from self.parse_listings(response, city=city, region=region, street=street)

    # ------------------------------------------------------------------ #
    # Listing page — extract house cards + handle pagination
    # ------------------------------------------------------------------ #
    def parse_listings(
        self,
        response: Response,
        city: str,
        region: str = "",
        street: str = "",
    ):
        """Parse a house listing page; follows pagination automatically."""
        cards = response.css("ul.sellListContent li.LOGCLICKDATA")

        for card in cards:
            detail_url = card.css("a.img::attr(href)").get()
            if not detail_url:
                continue
            detail_url = response.urljoin(detail_url)
            yield scrapy.Request(
                detail_url,
                callback=self.parse_detail,
                cb_kwargs={"city": city, "region": region, "street": street},
                errback=self.handle_error,
            )

        # Pagination: follow "next page" link
        next_page = response.css("a.next::attr(href)").get()
        if next_page:
            yield scrapy.Request(
                response.urljoin(next_page),
                callback=self.parse_listings,
                cb_kwargs={"city": city, "region": region, "street": street},
                errback=self.handle_error,
            )

    # ------------------------------------------------------------------ #
    # Detail page — extract full house fields
    # ------------------------------------------------------------------ #
    def parse_detail(self, response: Response, city: str, region: str, street: str):
        """Extract all house fields from a listing detail page."""
        item = HouseItem()

        item["url"] = response.url
        item["city"] = city
        item["region"] = region
        item["street"] = street

        # Title
        item["title"] = (
            response.css("h1.main::text").get()
            or response.css("title::text").get("")
        ).strip()

        # Community / neighbourhood name
        item["community"] = response.css(
            "div.communityName a.info::text"
        ).get("").strip()

        # Total price
        price_wan = response.css("span.total::text").get("0").strip()
        try:
            item["price"] = int(float(price_wan) * 10000)
        except ValueError:
            item["price"] = 0

        # House info section (houseInfo)
        house_info = response.css("div.houseInfo::text").getall()
        house_info_text = " ".join(house_info)

        # Area (m²)
        area_match = re.search(r"(\d+(?:\.\d+)?)\s*平米", house_info_text)
        item["area"] = float(area_match.group(1)) if area_match else None

        # Rooms
        rooms_match = re.search(r"(\d+)室", house_info_text)
        item["rooms"] = int(rooms_match.group(1)) if rooms_match else None

        # Floor
        floor_match = re.search(r"(\d+)\s*层", house_info_text)
        item["floor"] = int(floor_match.group(1)) if floor_match else None

        # Decoration
        deco_match = re.search(r"(精装|简装|毛坯|豪装)", house_info_text)
        item["decoration"] = deco_match.group(1) if deco_match else None

        # Age (building year → derive age)
        year_match = re.search(r"(\d{4})年建", house_info_text)
        if year_match:
            import datetime
            build_year = int(year_match.group(1))
            item["age"] = datetime.date.today().year - build_year
        else:
            item["age"] = None

        # Images
        item["images"] = response.css(
            "div.thumbnail img::attr(src)"
        ).getall() or []

        # Coordinates
        lat, lon = self._extract_coordinates(response)
        item["latitude"] = lat
        item["longitude"] = lon

        yield item

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _extract_coordinates(self, response: Response) -> tuple[float | None, float | None]:
        """
        Extract WGS-84 coordinates from embedded page scripts.
        Returns (None, None) if not found.
        """
        scripts = response.css("script::text").getall()
        for script in scripts:
            # Pattern 1: var resblockPosition = "lat,lon"
            m = re.search(r'resblockPosition\s*[=:]\s*["\']?([\d.]+),([\d.]+)', script)
            if m:
                try:
                    return float(m.group(1)), float(m.group(2))
                except ValueError:
                    pass
            # Pattern 2: JSON "lat": ..., "lng": ...
            m2 = re.search(r'"lat"\s*:\s*([\d.]+).*?"lng"\s*:\s*([\d.]+)', script)
            if m2:
                try:
                    return float(m2.group(1)), float(m2.group(2))
                except ValueError:
                    pass
        return None, None

    def handle_error(self, failure):
        logger.error("Request failed: %s — %s", failure.request.url, repr(failure))
