from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import BillingInterval, SubscriptionStatus, SubscriptionTier

if TYPE_CHECKING:
    from app.models.firms import Firm


class Subscription(BaseModel):
    """Tracks a firm's Stripe subscription lifecycle."""

    firm_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    stripe_price_id: Mapped[str | None] = mapped_column(String, nullable=True)
    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, name="subscription_tier", create_type=False),
        nullable=False,
        server_default="starter",
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status", native_enum=True),
        nullable=False,
        server_default="active",
    )
    billing_interval: Mapped[BillingInterval] = mapped_column(
        Enum(BillingInterval, name="billing_interval", native_enum=True),
        nullable=False,
        server_default="month",
    )
    current_period_start: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    canceled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    trial_end: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Dunning / grace period
    grace_period_end: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_payment_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    failed_payment_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Usage tracking (denormalized for fast checks)
    matter_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    user_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Last invoice info
    last_invoice_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)  # cents
    last_invoice_paid_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )

    firm: Mapped[Firm] = relationship(back_populates="subscription")
