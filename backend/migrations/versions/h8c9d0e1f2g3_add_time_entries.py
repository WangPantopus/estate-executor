"""Add time_entries table.

Revision ID: h8c9d0e1f2g3
Revises: g7b8c9d0e1f2
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "h8c9d0e1f2g3"
down_revision: str | None = "g7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "time_entrys",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("matter_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("stakeholder_id", sa.UUID(), nullable=False),
        sa.Column("hours", sa.Integer(), server_default="0", nullable=False),
        sa.Column("minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("billable", sa.Boolean(), server_default="true", nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["matter_id"], ["matters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["stakeholder_id"], ["stakeholders.id"], ondelete="CASCADE"),
    )

    op.create_index("ix_time_entries_matter_id", "time_entrys", ["matter_id"])
    op.create_index("ix_time_entries_task_id", "time_entrys", ["task_id"])
    op.create_index("ix_time_entries_stakeholder_id", "time_entrys", ["stakeholder_id"])
    op.create_index("ix_time_entries_entry_date", "time_entrys", ["entry_date"])


def downgrade() -> None:
    op.drop_index("ix_time_entries_entry_date", table_name="time_entrys")
    op.drop_index("ix_time_entries_stakeholder_id", table_name="time_entrys")
    op.drop_index("ix_time_entries_task_id", table_name="time_entrys")
    op.drop_index("ix_time_entries_matter_id", table_name="time_entrys")
    op.drop_table("time_entrys")
