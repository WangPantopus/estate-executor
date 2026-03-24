"""Add dispute resolution fields to communications table.

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "g7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

dispute_status_enum = postgresql.ENUM(
    "open",
    "under_review",
    "resolved",
    name="dispute_status",
    create_type=False,
)


def upgrade() -> None:
    # Create the dispute_status enum type
    dispute_status_enum.create(op.get_bind(), checkfirst=True)

    # Add dispute-specific columns to communications
    op.add_column(
        "communications",
        sa.Column("disputed_entity_type", sa.String(), nullable=True),
    )
    op.add_column(
        "communications",
        sa.Column("disputed_entity_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "communications",
        sa.Column("dispute_status", dispute_status_enum, nullable=True),
    )
    op.add_column(
        "communications",
        sa.Column("dispute_resolution_note", sa.String(), nullable=True),
    )
    op.add_column(
        "communications",
        sa.Column("dispute_resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "communications",
        sa.Column(
            "dispute_resolved_by",
            sa.UUID(),
            sa.ForeignKey("stakeholders.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Index for looking up active disputes by entity
    op.create_index(
        "ix_communications_dispute_entity",
        "communications",
        ["disputed_entity_type", "disputed_entity_id"],
        postgresql_where=sa.text("type = 'dispute_flag'"),
    )
    op.create_index(
        "ix_communications_dispute_status",
        "communications",
        ["dispute_status"],
        postgresql_where=sa.text("type = 'dispute_flag'"),
    )

    # Backfill existing dispute_flag communications: parse entity info from subject
    # Subject format is "Dispute: {entity_type} {entity_id}"
    op.execute("""
        UPDATE communications
        SET dispute_status = 'open',
            disputed_entity_type = split_part(
                replace(subject, 'Dispute: ', ''), ' ', 1
            ),
            disputed_entity_id = CASE
                WHEN split_part(replace(subject, 'Dispute: ', ''), ' ', 2) ~ '^[0-9a-f-]+$'
                THEN split_part(replace(subject, 'Dispute: ', ''), ' ', 2)::uuid
                ELSE NULL
            END
        WHERE type = 'dispute_flag'
          AND dispute_status IS NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_communications_dispute_status", table_name="communications")
    op.drop_index("ix_communications_dispute_entity", table_name="communications")
    op.drop_column("communications", "dispute_resolved_by")
    op.drop_column("communications", "dispute_resolved_at")
    op.drop_column("communications", "dispute_resolution_note")
    op.drop_column("communications", "dispute_status")
    op.drop_column("communications", "disputed_entity_id")
    op.drop_column("communications", "disputed_entity_type")
    dispute_status_enum.drop(op.get_bind(), checkfirst=True)
