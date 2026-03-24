"""Add integration_connections table for third-party integrations.

Revision ID: j0e1f2g3h4i5
Revises: i9d0e1f2g3h4
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "j0e1f2g3h4i5"
down_revision: str | None = "i9d0e1f2g3h4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    integration_provider = postgresql.ENUM(
        "clio",
        "quickbooks",
        "xero",
        "docusign",
        name="integration_provider",
        create_type=False,
    )
    integration_provider.create(op.get_bind(), checkfirst=True)

    integration_status = postgresql.ENUM(
        "connected",
        "disconnected",
        "error",
        "pending",
        name="integration_status",
        create_type=False,
    )
    integration_status.create(op.get_bind(), checkfirst=True)

    sync_status = postgresql.ENUM(
        "idle",
        "syncing",
        "success",
        "failed",
        name="sync_status",
        create_type=False,
    )
    sync_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "integration_connections",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("firm_id", sa.UUID(), nullable=False),
        sa.Column("provider", integration_provider, nullable=False),
        sa.Column("status", integration_status, server_default="disconnected", nullable=False),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("external_account_id", sa.String(), nullable=True),
        sa.Column("external_account_name", sa.String(), nullable=True),
        sa.Column("last_sync_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_sync_status", sync_status, server_default="idle", nullable=False),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column("sync_cursor", sa.String(), nullable=True),
        sa.Column("settings", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("field_mappings", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("entity_map", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("connected_by", sa.UUID(), nullable=True),
        sa.Column("disconnected_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("firm_id", "provider", name="uq_integration_firm_provider"),
    )
    op.create_index("ix_integration_connections_firm_id", "integration_connections", ["firm_id"])


def downgrade() -> None:
    op.drop_index("ix_integration_connections_firm_id", table_name="integration_connections")
    op.drop_table("integration_connections")
    op.execute("DROP TYPE IF EXISTS sync_status")
    op.execute("DROP TYPE IF EXISTS integration_status")
    op.execute("DROP TYPE IF EXISTS integration_provider")
