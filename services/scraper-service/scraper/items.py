"""
Scrapy item definitions for house scraping.
"""
import scrapy


class HouseItem(scrapy.Item):
    # Source
    url = scrapy.Field()
    # Basic info
    title = scrapy.Field()
    community = scrapy.Field()
    city = scrapy.Field()
    region = scrapy.Field()
    street = scrapy.Field()
    # Property details
    price = scrapy.Field()        # Total price (local currency)
    area = scrapy.Field()         # m²
    rooms = scrapy.Field()
    floor = scrapy.Field()
    decoration = scrapy.Field()   # e.g. renovated, original, new
    age = scrapy.Field()          # Years since construction
    images = scrapy.Field()       # List of image URLs
    # Coordinates (WGS-84)
    latitude = scrapy.Field()
    longitude = scrapy.Field()
