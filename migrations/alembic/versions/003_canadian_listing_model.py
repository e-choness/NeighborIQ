"""canadian_listing_model

Revision ID: 003_canadian_listing_model
Revises: 002_ai_tables_and_postgis
Create Date: 2026-09-24 00:00:00

Moves the listing model from the legacy Lianjia shape to Canadian listings:
- house_houses: property type, sqft, bathrooms, parking, postal code, carrying
  costs (condo fee, property tax), listing lifecycle (status, listed_at) and
  provenance (source, is_synthetic)
- house_rent_benchmarks: reference rents by city and bedroom count (CMHC format)
- POI tables: osm_id for idempotent OpenStreetMap reloads; transit mode
- house_price_predictions: one row per (house, model_version) instead of an
  ever-growing log
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_canadian_listing_model"
down_revision: Union[str, None] = "002_ai_tables_and_postgis"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None

_HOUSE_COLUMNS = [
    sa.Column("postal_code", sa.String(length=7), nullable=True),
    sa.Column("property_type", sa.String(length=30), nullable=True),
    sa.Column("sqft", sa.Integer(), nullable=True),
    sa.Column("bathrooms", sa.Numeric(precision=3, scale=1), nullable=True),
    sa.Column("parking", sa.Integer(), nullable=True),
    sa.Column("condo_fee", sa.Integer(), nullable=True),
    sa.Column("property_tax", sa.Integer(), nullable=True),
    sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
    sa.Column("listed_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("source", sa.String(length=30), nullable=False, server_default="seed"),
    sa.Column("is_synthetic", sa.Integer(), nullable=False, server_default="0"),
]


def upgrade() -> None:
    for column in _HOUSE_COLUMNS:
        op.add_column("house_houses", column)
    op.create_index("ix_house_houses_postal_code", "house_houses", ["postal_code"])
    op.create_index("ix_house_houses_property_type", "house_houses", ["property_type"])
    op.create_index("idx_house_houses_comps", "house_houses", ["city", "property_type", "rooms"])
    # Backfill sqft for rows that only carry m²
    op.execute("UPDATE house_houses SET sqft = ROUND(area * 10.7639) WHERE sqft IS NULL AND area > 0")

    op.create_table(
        "house_rent_benchmarks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("bedrooms", sa.Integer(), nullable=False),
        sa.Column("avg_rent", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("survey_date", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city", "bedrooms", name="uq_rent_benchmark_city_beds"),
    )

    for table in ("house_schools", "house_hospitals", "house_bus_stops"):
        op.add_column(table, sa.Column("osm_id", sa.String(length=32), nullable=True))
        op.create_unique_constraint(f"uq_{table}_osm_id", table, ["osm_id"])
    op.add_column("house_bus_stops", sa.Column("mode", sa.String(length=20), nullable=True))

    # Keep only the newest prediction per (house, model_version), then enforce it
    op.execute(
        """
        DELETE FROM house_price_predictions p
        USING house_price_predictions newer
        WHERE p.house_id = newer.house_id
          AND p.model_version = newer.model_version
          AND p.predicted_at < newer.predicted_at
        """
    )
    op.create_unique_constraint(
        "uq_price_prediction_house_model",
        "house_price_predictions",
        ["house_id", "model_version"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_price_prediction_house_model", "house_price_predictions", type_="unique")
    op.drop_column("house_bus_stops", "mode")
    for table in ("house_schools", "house_hospitals", "house_bus_stops"):
        op.drop_constraint(f"uq_{table}_osm_id", table, type_="unique")
        op.drop_column(table, "osm_id")
    op.drop_table("house_rent_benchmarks")
    op.drop_index("idx_house_houses_comps", table_name="house_houses")
    op.drop_index("ix_house_houses_property_type", table_name="house_houses")
    op.drop_index("ix_house_houses_postal_code", table_name="house_houses")
    for column in reversed(_HOUSE_COLUMNS):
        op.drop_column("house_houses", column.name)
