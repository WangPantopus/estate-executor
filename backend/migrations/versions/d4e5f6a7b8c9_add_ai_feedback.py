"""add ai_feedback table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-23 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_feedback",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("firm_id", sa.UUID(), nullable=False),
        sa.Column("matter_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("feedback_type", sa.String(), nullable=False),
        sa.Column("ai_output", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("user_correction", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("corrected_by", sa.UUID(), nullable=True),
        sa.Column("model_used", sa.String(), nullable=True),
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
    op.create_index("ix_ai_feedback_firm_id_created_at", "ai_feedback", ["firm_id", "created_at"])
    op.create_index("ix_ai_feedback_feedback_type", "ai_feedback", ["feedback_type"])
    op.create_index("ix_ai_feedback_entity_id", "ai_feedback", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_feedback_entity_id", table_name="ai_feedback")
    op.drop_index("ix_ai_feedback_feedback_type", table_name="ai_feedback")
    op.drop_index("ix_ai_feedback_firm_id_created_at", table_name="ai_feedback")
    op.drop_table("ai_feedback")
