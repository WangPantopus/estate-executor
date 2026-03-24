"""Add distributions table.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create distribution_type enum
    distribution_type_enum = sa.Enum(
        "cash",
        "asset_transfer",
        "in_kind",
        name="distribution_type",
    )
    distribution_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "distributions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("matter_id", sa.UUID(), nullable=False),
        sa.Column("asset_id", sa.UUID(), nullable=True),
        sa.Column("beneficiary_stakeholder_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column(
            "distribution_type",
            sa.Enum(
                "cash",
                "asset_transfer",
                "in_kind",
                name="distribution_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("distribution_date", sa.Date(), nullable=False),
        sa.Column("receipt_acknowledged", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("receipt_acknowledged_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["matter_id"], ["matters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["beneficiary_stakeholder_id"], ["stakeholders.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_distributions_matter_id", "distributions", ["matter_id"])
    op.create_index("ix_distributions_beneficiary", "distributions", ["beneficiary_stakeholder_id"])


def downgrade() -> None:
    op.drop_index("ix_distributions_beneficiary", table_name="distributions")
    op.drop_index("ix_distributions_matter_id", table_name="distributions")
    op.drop_table("distributions")
    sa.Enum(name="distribution_type").drop(op.get_bind(), checkfirst=True)
