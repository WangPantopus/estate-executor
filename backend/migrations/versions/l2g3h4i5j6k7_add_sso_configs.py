"""Add sso_configs table for enterprise SSO.

Revision ID: l2g3h4i5j6k7
Revises: k1f2g3h4i5j6
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "l2g3h4i5j6k7"
down_revision: str | None = "k1f2g3h4i5j6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sso_configs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("firm_id", sa.UUID(), nullable=False),
        sa.Column("protocol", sa.String(), server_default="saml", nullable=False),
        sa.Column("saml_metadata_url", sa.Text(), nullable=True),
        sa.Column("saml_metadata_xml", sa.Text(), nullable=True),
        sa.Column("saml_entity_id", sa.String(), nullable=True),
        sa.Column("saml_sso_url", sa.String(), nullable=True),
        sa.Column("saml_certificate", sa.Text(), nullable=True),
        sa.Column("oidc_discovery_url", sa.String(), nullable=True),
        sa.Column("oidc_client_id", sa.String(), nullable=True),
        sa.Column("oidc_client_secret", sa.Text(), nullable=True),
        sa.Column("auth0_connection_id", sa.String(), nullable=True),
        sa.Column("auth0_connection_name", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("enforce_sso", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("auto_provision", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("default_role", sa.String(), server_default="member", nullable=False),
        sa.Column("allowed_domains", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("configured_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("firm_id"),
    )
    op.create_index("ix_sso_configs_firm_id", "sso_configs", ["firm_id"])


def downgrade() -> None:
    op.drop_index("ix_sso_configs_firm_id", table_name="sso_configs")
    op.drop_table("sso_configs")
