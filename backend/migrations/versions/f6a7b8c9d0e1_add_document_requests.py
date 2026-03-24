"""Add document_requests table.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

document_request_status_enum = postgresql.ENUM(
    "pending", "uploaded", "expired",
    name="document_request_status",
    create_type=False,
)


def upgrade() -> None:
    # Create enum type
    document_request_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "document_requests",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("matter_id", sa.UUID(), nullable=False),
        sa.Column("requester_stakeholder_id", sa.UUID(), nullable=False),
        sa.Column("target_stakeholder_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("doc_type_needed", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column(
            "upload_token", sa.String(), nullable=False, unique=True,
        ),
        sa.Column(
            "status",
            document_request_status_enum,
            server_default="pending",
            nullable=False,
        ),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column(
            "expires_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
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
        sa.ForeignKeyConstraint(
            ["requester_stakeholder_id"], ["stakeholders.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_stakeholder_id"], ["stakeholders.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_document_requests_token", "document_requests", ["upload_token"], unique=True)
    op.create_index("ix_document_requests_matter_id", "document_requests", ["matter_id"])
    op.create_index("ix_document_requests_status", "document_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_document_requests_status", table_name="document_requests")
    op.drop_index("ix_document_requests_matter_id", table_name="document_requests")
    op.drop_index("ix_document_requests_token", table_name="document_requests")
    op.drop_table("document_requests")
    document_request_status_enum.drop(op.get_bind(), checkfirst=True)
