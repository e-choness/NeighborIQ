"""
Item validation pipeline.

Enforces data quality rules before any item reaches the database:
  - price > 0
  - Non-null community (must have a community name)
  - rooms in [1, 10]
  - area in [10, 500] m²

Items failing validation are dropped with a logged reason.
"""
import logging

from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)


class ValidationPipeline:
    """Validates house items and drops those that fail quality rules."""

    def process_item(self, item, spider):
        errors = []

        # Price > 0
        price = item.get("price")
        try:
            price = int(price)
        except (TypeError, ValueError):
            price = 0
        if price <= 0:
            errors.append(f"invalid price: {price!r}")
        else:
            item["price"] = price

        # Community must be non-null / non-empty
        community = item.get("community")
        if not community or not str(community).strip():
            errors.append("missing community")

        # Rooms: 1–10
        rooms = item.get("rooms")
        if rooms is not None:
            try:
                rooms = int(rooms)
            except (TypeError, ValueError):
                rooms = None
            if rooms is not None and not (1 <= rooms <= 10):
                errors.append(f"rooms out of range: {rooms}")
            else:
                item["rooms"] = rooms

        # Area: 10–500 m²
        area = item.get("area")
        if area is not None:
            try:
                area = float(area)
            except (TypeError, ValueError):
                area = None
            if area is not None and not (10.0 <= area <= 500.0):
                errors.append(f"area out of range: {area}")
            else:
                item["area"] = area

        if errors:
            url = item.get("url", "unknown")
            raise DropItem(f"Validation failed for {url}: {'; '.join(errors)}")

        return item
