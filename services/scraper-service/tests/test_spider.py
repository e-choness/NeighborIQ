"""
Tests for LianjiaHouseSpider.

Uses Scrapy's fake_response utility (built from static HTML) to test
parsing logic without making real HTTP requests. HTML samples reflect
the current spider implementation; update when the spider is rewritten
for the Canadian data source.
"""
from unittest.mock import MagicMock

import pytest
from scrapy.http import HtmlResponse, Request

from scraper.items import HouseItem
from scraper.spiders.house_spider import LianjiaHouseSpider


def _fake_response(url: str, html: str) -> HtmlResponse:
    """Construct a HtmlResponse from a string for testing."""
    return HtmlResponse(
        url=url,
        body=html.encode("utf-8"),
        encoding="utf-8",
        request=Request(url=url),
    )


SAMPLE_DETAIL_HTML = """
<html>
<head><title>3室2厅 精装 Nanjing House - 链家</title></head>
<body>
  <h1 class="main">精装大三室 鼓楼核心地段</h1>
  <div class="communityName"><a class="info">江南锦苑</a></div>
  <span class="total">350</span>
  <div class="houseInfo">
    3室2厅 120.5平米 精装 15层 2008年建
  </div>
  <div class="thumbnail">
    <img src="https://img.lianjia.com/house1.jpg"/>
    <img src="https://img.lianjia.com/house2.jpg"/>
  </div>
  <script>
    var resblockPosition = "32.0638,118.7965";
  </script>
</body>
</html>
"""

SAMPLE_LISTING_HTML = """
<html>
<body>
  <ul class="sellListContent">
    <li class="LOGCLICKDATA">
      <a class="img" href="/ershoufang/101000000000001.html">House 1</a>
    </li>
    <li class="LOGCLICKDATA">
      <a class="img" href="/ershoufang/101000000000002.html">House 2</a>
    </li>
  </ul>
  <a class="next" href="/ershoufang/gulou/pg2/">下一页</a>
</body>
</html>
"""

SAMPLE_CITY_HTML = """
<html>
<body>
  <div class="areaList">
    <a href="/ershoufang/gulou/">鼓楼</a>
    <a href="/ershoufang/jianye/">建邺</a>
    <a href="/ershoufang/">首页</a>
  </div>
</body>
</html>
"""


class TestLianjiaHouseSpider:
    def _spider(self):
        # Mock the crawler via the class attribute Scrapy resolves at call time
        spider = LianjiaHouseSpider.__new__(LianjiaHouseSpider)
        spider.cities = ["nanjing"]
        # logger is a read-only property on Spider — do not set it; use the default
        spider.crawler = MagicMock()
        return spider

    # ---- Detail page parsing -----------------------------------------------

    def test_parse_detail_title(self):
        spider = self._spider()
        response = _fake_response(
            "https://nanjing.lianjia.com/ershoufang/101000000000001.html",
            SAMPLE_DETAIL_HTML,
        )
        results = list(spider.parse_detail(response, city="nanjing", region="gulou", street=""))
        assert len(results) == 1
        item = results[0]
        assert "精装大三室" in item["title"]

    def test_parse_detail_community(self):
        spider = self._spider()
        response = _fake_response(
            "https://nanjing.lianjia.com/ershoufang/101000000000001.html",
            SAMPLE_DETAIL_HTML,
        )
        results = list(spider.parse_detail(response, city="nanjing", region="gulou", street=""))
        assert results[0]["community"] == "江南锦苑"

    def test_parse_detail_price_conversion(self):
        """350 万 should become 3,500,000 yuan."""
        spider = self._spider()
        response = _fake_response(
            "https://nanjing.lianjia.com/ershoufang/101000000000001.html",
            SAMPLE_DETAIL_HTML,
        )
        results = list(spider.parse_detail(response, city="nanjing", region="gulou", street=""))
        assert results[0]["price"] == 3_500_000

    def test_parse_detail_area(self):
        spider = self._spider()
        response = _fake_response(
            "https://nanjing.lianjia.com/ershoufang/101000000000001.html",
            SAMPLE_DETAIL_HTML,
        )
        results = list(spider.parse_detail(response, city="nanjing", region="gulou", street=""))
        assert results[0]["area"] == 120.5

    def test_parse_detail_rooms(self):
        spider = self._spider()
        response = _fake_response(
            "https://nanjing.lianjia.com/ershoufang/101000000000001.html",
            SAMPLE_DETAIL_HTML,
        )
        results = list(spider.parse_detail(response, city="nanjing", region="gulou", street=""))
        assert results[0]["rooms"] == 3

    def test_parse_detail_coordinates_extracted(self):
        spider = self._spider()
        response = _fake_response(
            "https://nanjing.lianjia.com/ershoufang/101000000000001.html",
            SAMPLE_DETAIL_HTML,
        )
        results = list(spider.parse_detail(response, city="nanjing", region="gulou", street=""))
        assert results[0]["latitude"] == pytest.approx(32.0638, abs=0.001)
        assert results[0]["longitude"] == pytest.approx(118.7965, abs=0.001)

    def test_parse_detail_images(self):
        spider = self._spider()
        response = _fake_response(
            "https://nanjing.lianjia.com/ershoufang/101000000000001.html",
            SAMPLE_DETAIL_HTML,
        )
        results = list(spider.parse_detail(response, city="nanjing", region="gulou", street=""))
        assert len(results[0]["images"]) == 2

    def test_parse_detail_url_set(self):
        spider = self._spider()
        url = "https://nanjing.lianjia.com/ershoufang/101000000000001.html"
        response = _fake_response(url, SAMPLE_DETAIL_HTML)
        results = list(spider.parse_detail(response, city="nanjing", region="gulou", street=""))
        assert results[0]["url"] == url

    # ---- Listing page parsing ----------------------------------------------

    def test_parse_listings_yields_requests(self):
        spider = self._spider()
        response = _fake_response(
            "https://nanjing.lianjia.com/ershoufang/gulou/",
            SAMPLE_LISTING_HTML,
        )
        results = list(spider.parse_listings(response, city="nanjing", region="gulou", street=""))
        # 2 detail requests + 1 next-page request
        assert len(results) == 3

    def test_parse_listings_follows_pagination(self):
        spider = self._spider()
        response = _fake_response(
            "https://nanjing.lianjia.com/ershoufang/gulou/",
            SAMPLE_LISTING_HTML,
        )
        results = list(spider.parse_listings(response, city="nanjing", region="gulou", street=""))
        # One of the results should be the next-page request
        next_requests = [r for r in results if hasattr(r, "url") and "pg2" in r.url]
        assert len(next_requests) == 1

    # ---- City page parsing -------------------------------------------------

    def test_parse_city_yields_region_requests(self):
        spider = self._spider()
        response = _fake_response(
            "https://nanjing.lianjia.com/ershoufang/",
            SAMPLE_CITY_HTML,
        )
        results = list(spider.parse_city(response, city="nanjing"))
        # Should yield requests for gulou and jianye (not the root /ershoufang/)
        assert len(results) == 2
        urls = [r.url for r in results]
        assert any("gulou" in u for u in urls)
        assert any("jianye" in u for u in urls)
