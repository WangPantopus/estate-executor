from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import FirmType, SubscriptionTier

if TYPE_CHECKING:
    from app.models.firm_memberships import FirmMembership
    from app.models.matters import Matter
    from app.models.subscriptions import Subscription


class Firm(BaseModel):
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    type: Mapped[FirmType] = mapped_column(
        Enum(FirmType, name="firm_type", native_enum=True),
        nullable=False,
    )
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, name="subscription_tier", native_enum=True),
        nullable=False,
        server_default="starter",
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    white_label: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    memberships: Mapped[list[FirmMembership]] = relationship(
        back_populates="firm", cascade="all, delete-orphan"
    )
    matters: Mapped[list[Matter]] = relationship(
        back_populates="firm", cascade="all, delete-orphan"
    )
    subscription: Mapped[Subscription | None] = relationship(
        back_populates="firm", cascade="all, delete-orphan", uselist=False
    )
