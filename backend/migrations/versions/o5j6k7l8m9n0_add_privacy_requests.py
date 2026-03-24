"""Add privacy_requests table for GDPR/CCPA compliance.

Revision ID: o5j6k7l8m9n0
Revises: n4i5j6k7l8m9
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "o5j6k7l8m9n0"
down_revision: str | None = "n4i5j6k7l8m9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum types explicitly, then use create_type=False in columns
    # to prevent op.create_table from trying to create them again.
    privacy_request_type = postgresql.ENUM(
        "data_export",
        "data_deletion",
        name="privacy_request_type",
        create_type=False,
    )
    privacy_request_status = postgresql.ENUM(
        "pending",
        "approved",
        "processing",
        "completed",
        "rejected",
        name="privacy_request_status",
        create_type=False,
    )
    privacy_request_type.create(op.get_bind(), checkfirst=True)
    privacy_request_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "privacy_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "firm_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("firms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_type", privacy_request_type, nullable=False),
        sa.Column("status", privacy_request_status, nullable=False, server_default="pending"),
        sa.Column("reason", sa.String, nullable=True),
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("review_note", sa.String, nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("export_storage_key", sa.String, nullable=True),
        sa.Column("deletion_summary", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_privacy_requests_user_id_status", "privacy_requests", ["user_id", "status"])
    op.create_index("ix_privacy_requests_firm_id_status", "privacy_requests", ["firm_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_privacy_requests_firm_id_status", table_name="privacy_requests")
    op.drop_index("ix_privacy_requests_user_id_status", table_name="privacy_requests")
    op.drop_table("privacy_requests")
    op.execute("DROP TYPE IF EXISTS privacy_request_status;")
    op.execute("DROP TYPE IF EXISTS privacy_request_type;")
