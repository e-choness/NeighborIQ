"""portfolio_saved_houses

Revision ID: 004_portfolio_saved_houses
Revises: 003_canadian_listing_model
Create Date: 2026-09-24 00:00:00

portfolio_saved_houses was only ever created by the portfolio service's
create_all at startup, never by a migration — so an Alembic-managed database
had no portfolio table. Adds it, with saved cash-flow assumptions per deal.
"""

from typing import Union

from alembic import op

revision: str = "004_portfolio_saved_houses"
down_revision: Union[str, None] = "003_canadian_listing_model"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_saved_houses (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
            house_id INTEGER NOT NULL REFERENCES house_houses(id) ON DELETE CASCADE,
            notes VARCHAR(512),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    # Databases created by the old service's create_all already have the table
    op.execute("ALTER TABLE portfolio_saved_houses ADD COLUMN IF NOT EXISTS assumptions TEXT")
    op.execute("CREATE INDEX IF NOT EXISTS ix_portfolio_saved_houses_id ON portfolio_saved_houses (id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_portfolio_saved_houses_user_id ON portfolio_saved_houses (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_portfolio_saved_houses_house_id ON portfolio_saved_houses (house_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_portfolio_saved_houses_user ON portfolio_saved_houses (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_portfolio_saved_houses_house ON portfolio_saved_houses (house_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_portfolio_saved_houses_user_house "
        "ON portfolio_saved_houses (user_id, house_id)"
    )


def downgrade() -> None:
    op.drop_table("portfolio_saved_houses")
