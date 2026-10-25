"""initial schema: manufacturers and devices

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "manufacturers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "name",
            sa.String(length=100, collation="NOCASE"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manufacturers")),
        sa.UniqueConstraint("name", name=op.f("uq_manufacturers_name")),
    )
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "inventory_number",
            sa.String(length=50, collation="NOCASE"),
            nullable=False,
        ),
        sa.Column("device_type", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("cost", sa.Float(), nullable=False),
        sa.Column("manufacturer_id", sa.Integer(), nullable=False),
        sa.CheckConstraint("cost >= 0", name=op.f("ck_devices_cost_non_negative")),
        sa.ForeignKeyConstraint(
            ["manufacturer_id"],
            ["manufacturers.id"],
            name=op.f("fk_devices_manufacturer_id_manufacturers"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_devices")),
        sa.UniqueConstraint("inventory_number", name=op.f("uq_devices_inventory_number")),
    )


def downgrade() -> None:
    op.drop_table("devices")
    op.drop_table("manufacturers")
