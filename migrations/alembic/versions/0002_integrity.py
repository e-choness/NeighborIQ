"""integrity: missing foreign keys, unique emails, redundant indexes

Revision ID: 0002_integrity
Revises: 0001_baseline
Create Date: 2026-09-24 00:00:01

The legacy migrations never created some constraints the models declare:

- house_price_history, the three amenity link tables and auth_refresh_tokens had
  no foreign keys, so deleting a listing (or user) left orphaned rows behind;
- auth_users.email was indexed but not unique.

Orphaned rows are deleted before the keys are added. Duplicate emails cannot be
resolved automatically; the upgrade stops and lists them.

It also drops indexes that duplicate another index or a unique constraint.
"""

from typing import Union

from alembic import op
from sqlalchemy import text

revision: str = "0002_integrity"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None

# (table, column, referenced table, constraint name)
FOREIGN_KEYS = (
    ("house_price_history", "house_id", "house_houses", "fk_house_price_history_house"),
    ("house_school_links", "house_id", "house_houses", "fk_house_school_links_house"),
    ("house_school_links", "school_id", "house_schools", "fk_house_school_links_school"),
    ("house_hospital_links", "house_id", "house_houses", "fk_house_hospital_links_house"),
    ("house_hospital_links", "hospital_id", "house_hospitals", "fk_house_hospital_links_hospital"),
    ("house_bus_links", "house_id", "house_houses", "fk_house_bus_links_house"),
    ("house_bus_links", "bus_stop_id", "house_bus_stops", "fk_house_bus_links_stop"),
    ("auth_refresh_tokens", "user_id", "auth_users", "fk_auth_refresh_tokens_user"),
)

# index → why it is redundant; recreated on downgrade
REDUNDANT_INDEXES = {
    "ix_portfolio_saved_houses_id": "CREATE INDEX ix_portfolio_saved_houses_id ON portfolio_saved_houses (id)",
    "ix_portfolio_saved_houses_user_id": (
        "CREATE INDEX ix_portfolio_saved_houses_user_id ON portfolio_saved_houses (user_id)"
    ),
    "ix_portfolio_saved_houses_house_id": (
        "CREATE INDEX ix_portfolio_saved_houses_house_id ON portfolio_saved_houses (house_id)"
    ),
    "idx_portfolio_saved_houses_user": (
        "CREATE INDEX idx_portfolio_saved_houses_user ON portfolio_saved_houses (user_id)"
    ),
    "idx_house_school_links_house": "CREATE INDEX idx_house_school_links_house ON house_school_links (house_id)",
    "idx_rental_yields_house": "CREATE INDEX idx_rental_yields_house ON house_rental_yields (house_id)",
    "idx_house_price_predictions_house": (
        "CREATE INDEX idx_house_price_predictions_house ON house_price_predictions (house_id)"
    ),
    "idx_house_houses_city_region": "CREATE INDEX idx_house_houses_city_region ON house_houses (city, region)",
}
# Covered by: the primary key; uq_portfolio_saved_houses_user_house (user_id, house_id);
# idx_portfolio_saved_houses_house; idx_house_school_links_composite (house_id, school_id);
# uq_rental_yields_house; uq_price_prediction_house_model (house_id, …);
# idx_house_houses_composite (city, region, price).


def upgrade() -> None:
    conn = op.get_bind()

    duplicates = conn.execute(
        text("SELECT email, count(*) FROM auth_users GROUP BY email HAVING count(*) > 1")
    ).all()
    if duplicates:
        listed = ", ".join(f"{email} (×{n})" for email, n in duplicates)
        raise RuntimeError(
            f"auth_users has duplicate emails: {listed}. Merge or delete the extra accounts, then re-run."
        )

    for table, column, ref, name in FOREIGN_KEYS:
        op.execute(f"DELETE FROM {table} t WHERE NOT EXISTS (SELECT 1 FROM {ref} r WHERE r.id = t.{column})")
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {name} "
            f"FOREIGN KEY ({column}) REFERENCES {ref}(id) ON DELETE CASCADE"
        )

    op.execute("ALTER TABLE auth_users ADD CONSTRAINT uq_auth_users_email UNIQUE (email)")
    op.execute("DROP INDEX IF EXISTS idx_auth_users_email")

    for index in REDUNDANT_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {index}")


def downgrade() -> None:
    for create in REDUNDANT_INDEXES.values():
        op.execute(create)
    op.execute("CREATE INDEX idx_auth_users_email ON auth_users (email)")
    op.execute("ALTER TABLE auth_users DROP CONSTRAINT uq_auth_users_email")
    for table, _, _, name in FOREIGN_KEYS:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")
