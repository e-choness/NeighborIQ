"""
Scrapy item for listings — mirrors the canonical format in ingestion/canonical.py.
"""

import scrapy


class ListingItem(scrapy.Item):
    # Identity / source
    url = scrapy.Field()  # Stable listing key (upsert target)
    source = scrapy.Field()
    is_synthetic = scrapy.Field()
    # Location
    title = scrapy.Field()
    city = scrapy.Field()
    region = scrapy.Field()
    community = scrapy.Field()  # Neighbourhood
    street = scrapy.Field()
    postal_code = scrapy.Field()
    latitude = scrapy.Field()
    longitude = scrapy.Field()
    # Property
    property_type = scrapy.Field()  # condo|townhouse|semi|detached
    price = scrapy.Field()  # Asking price, CAD
    sqft = scrapy.Field()
    area = scrapy.Field()  # m² (derived from sqft when absent)
    rooms = scrapy.Field()  # Bedrooms
    bathrooms = scrapy.Field()
    parking = scrapy.Field()
    floor = scrapy.Field()
    decoration = scrapy.Field()
    age = scrapy.Field()
    images = scrapy.Field()
    # Carrying costs and lifecycle
    condo_fee = scrapy.Field()  # Monthly, CAD
    property_tax = scrapy.Field()  # Annual, CAD
    status = scrapy.Field()
    listed_at = scrapy.Field()
    price_history = scrapy.Field()


# Backwards-compatible alias for older imports
HouseItem = ListingItem
