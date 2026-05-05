"""ai_tables_and_postgis

Revision ID: 002_ai_tables_and_postgis
Revises: 001_initial_schema
Create Date: 2026-05-05 00:00:00

Adds:
- PostGIS extension (for geo-spatial queries in Phase 5+)
- house_price_predictions (ML model outputs)
- house_rental_yields (formula-based rental estimates)
- house_market_insights (LLM-generated city narratives)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002_ai_tables_and_postgis"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # PostGIS extension — required for Phase 2A geo-spatial support
    # CREATE EXTENSION IF NOT EXISTS is idempotent; safe to run multiple times.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # AI domain: price predictions from XGBoost/LightGBM
    op.create_table(
        "house_price_predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("house_id", sa.Integer(), nullable=False),
        sa.Column("predicted_price", sa.Integer(), nullable=False),
        sa.Column("price_low", sa.Integer(), nullable=False),
        sa.Column("price_high", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column(
            "predicted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["house_id"], ["house_houses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_house_price_predictions_house", "house_price_predictions", ["house_id"]
    )
    op.create_index(
        "idx_house_price_predictions_at", "house_price_predictions", ["predicted_at"]
    )

    # AI domain: formula-based rental yield estimates (one row per house)
    op.create_table(
        "house_rental_yields",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("house_id", sa.Integer(), nullable=False),
        sa.Column("annual_rent", sa.Integer(), nullable=False),
        sa.Column("gross_yield", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("net_yield", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["house_id"], ["house_houses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("house_id", name="uq_rental_yields_house"),
    )
    op.create_index("idx_rental_yields_house", "house_rental_yields", ["house_id"])

    # AI domain: LLM-generated city/region market narratives (one per city per day)
    op.create_table(
        "house_market_insights",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_market_insights_city", "house_market_insights", ["city"])
    op.create_index(
        "idx_market_insights_computed_at", "house_market_insights", ["computed_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_market_insights_computed_at", table_name="house_market_insights")
    op.drop_index("idx_market_insights_city", table_name="house_market_insights")
    op.drop_table("house_market_insights")

    op.drop_index("idx_rental_yields_house", table_name="house_rental_yields")
    op.drop_table("house_rental_yields")

    op.drop_index("idx_house_price_predictions_at", table_name="house_price_predictions")
    op.drop_index("idx_house_price_predictions_house", table_name="house_price_predictions")
    op.drop_table("house_price_predictions")

    # Note: PostGIS extension is not dropped on downgrade — removing it could break
    # other objects in the database that depend on it.
