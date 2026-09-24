"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

What changes and why (the schema is documented in docs/architecture/data-models.md).
"""

from typing import Union

from alembic import op
${imports if imports else ""}
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, None] = ${repr(branch_labels)}
depends_on: Union[str, None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else 'op.execute("""\n        -- SQL here\n    """)'}


def downgrade() -> None:
    ${downgrades if downgrades else 'op.execute("""\n        -- undo the upgrade\n    """)'}
