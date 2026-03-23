"""add ai_usage_logs table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-23 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("firm_id", sa.UUID(), nullable=False),
        sa.Column("matter_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_estimate_usd", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), server_default=sa.text("'success'"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_usage_logs_firm_id_created_at", "ai_usage_logs", ["firm_id", "created_at"]
    )
    op.create_index("ix_ai_usage_logs_matter_id", "ai_usage_logs", ["matter_id"])
    op.create_index("ix_ai_usage_logs_operation", "ai_usage_logs", ["operation"])


def downgrade() -> None:
    op.drop_index("ix_ai_usage_logs_operation", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_matter_id", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_firm_id_created_at", table_name="ai_usage_logs")
    op.drop_table("ai_usage_logs")
