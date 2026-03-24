"""Add subscriptions table for Stripe billing.

Revision ID: i9d0e1f2g3h4
Revises: h8c9d0e1f2g3
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "i9d0e1f2g3h4"
down_revision: str | None = "h8c9d0e1f2g3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create new enum types
    subscription_status_enum = postgresql.ENUM(
        "trialing",
        "active",
        "past_due",
        "canceled",
        "unpaid",
        "incomplete",
        "paused",
        name="subscription_status",
        create_type=False,
    )
    subscription_status_enum.create(op.get_bind(), checkfirst=True)

    billing_interval_enum = postgresql.ENUM(
        "month",
        "year",
        name="billing_interval",
        create_type=False,
    )
    billing_interval_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "subscriptions",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("firm_id", sa.UUID(), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
        sa.Column("stripe_price_id", sa.String(), nullable=True),
        sa.Column(
            "tier",
            postgresql.ENUM(
                "starter",
                "professional",
                "growth",
                "enterprise",
                name="subscription_tier",
                create_type=False,
            ),
            server_default="starter",
            nullable=False,
        ),
        sa.Column(
            "status",
            subscription_status_enum,
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "billing_interval",
            billing_interval_enum,
            server_default="month",
            nullable=False,
        ),
        sa.Column(
            "current_period_start",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "current_period_end",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("canceled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("trial_end", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "grace_period_end", sa.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("last_payment_error", sa.Text(), nullable=True),
        sa.Column(
            "failed_payment_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "matter_count", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "user_count", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("last_invoice_amount", sa.Integer(), nullable=True),
        sa.Column(
            "last_invoice_paid_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
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
        sa.ForeignKeyConstraint(
            ["firm_id"],
            ["firms.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("firm_id"),
        sa.UniqueConstraint("stripe_subscription_id"),
    )

    op.create_index(
        "ix_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
    )
    op.create_index(
        "ix_subscriptions_status",
        "subscriptions",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index(
        "ix_subscriptions_stripe_subscription_id",
        table_name="subscriptions",
    )
    op.drop_table("subscriptions")

    op.execute("DROP TYPE IF EXISTS billing_interval")
    op.execute("DROP TYPE IF EXISTS subscription_status")
