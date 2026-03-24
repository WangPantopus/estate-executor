"""Add signature_requests table for DocuSign e-signatures.

Revision ID: k1f2g3h4i5j6
Revises: j0e1f2g3h4i5
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "k1f2g3h4i5j6"
down_revision: str | None = "j0e1f2g3h4i5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    sig_status = postgresql.ENUM(
        "draft", "sent", "delivered", "signed", "completed",
        "declined", "voided", "expired",
        name="signature_request_status", create_type=False,
    )
    sig_status.create(op.get_bind(), checkfirst=True)

    sig_type = postgresql.ENUM(
        "distribution_consent", "beneficiary_acknowledgment",
        "executor_oath", "general",
        name="signature_request_type", create_type=False,
    )
    sig_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "signature_requests",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("matter_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("request_type", sig_type, server_default="general", nullable=False),
        sa.Column("status", sig_status, server_default="draft", nullable=False),
        sa.Column("envelope_id", sa.String(), nullable=True),
        sa.Column("envelope_uri", sa.String(), nullable=True),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("sent_by", sa.UUID(), nullable=False),
        sa.Column("signers", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("voided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("signed_document_id", sa.UUID(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["matter_id"], ["matters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sent_by"], ["stakeholders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("envelope_id"),
    )
    op.create_index("ix_signature_requests_matter_id", "signature_requests", ["matter_id"])
    op.create_index("ix_signature_requests_envelope_id", "signature_requests", ["envelope_id"])


def downgrade() -> None:
    op.drop_index("ix_signature_requests_envelope_id", table_name="signature_requests")
    op.drop_index("ix_signature_requests_matter_id", table_name="signature_requests")
    op.drop_table("signature_requests")
    op.execute("DROP TYPE IF EXISTS signature_request_type")
    op.execute("DROP TYPE IF EXISTS signature_request_status")
