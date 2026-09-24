"""
Coordinate pipeline — pass-through.

Canadian real estate data is already in WGS-84 (standard GPS coordinates),
so no coordinate conversion is needed. This pipeline passes items through unchanged.
"""


class CoordinateConversionPipeline:
    """No-op pipeline. Coordinates are passed through unchanged."""

    def process_item(self, item, spider):
        return item
