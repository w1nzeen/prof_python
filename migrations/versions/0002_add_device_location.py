"""add device location

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("devices") as batch:
        batch.add_column(
            sa.Column("location", sa.String(length=100), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("devices") as batch:
        batch.drop_column("location")
