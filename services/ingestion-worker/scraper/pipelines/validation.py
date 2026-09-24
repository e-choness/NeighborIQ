"""
Item validation pipeline.

Applies the shared canonical rules (ingestion/canonical.py) so feed ingestion
and the CLI loaders accept and reject exactly the same listings. Items failing
validation are dropped with a logged reason.
"""

import logging

from scrapy.exceptions import DropItem

from ingestion.canonical import normalize, validate

logger = logging.getLogger(__name__)


class ValidationPipeline:
    """Normalizes listing items and drops those that fail quality rules."""

    def process_item(self, item, spider):
        normalized = normalize(dict(item))
        errors = validate(normalized)
        if errors:
            url = item.get("url", "unknown")
            raise DropItem(f"Validation failed for {url}: {'; '.join(errors)}")

        for key, value in normalized.items():
            if key in item.fields:
                item[key] = value
        return item
