"""Webhook + WebhookDelivery models — outbound webhook management."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.firms import Firm


class Webhook(BaseModel):
    """Outbound webhook endpoint configuration."""

    firm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Secret for HMAC-SHA256 signature verification
    secret: Mapped[str] = mapped_column(String(128), nullable=False)

    # Subscribed events — e.g. ["matter.created", "task.updated", "document.uploaded"]
    events: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    # Metadata
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    failure_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    firm: Mapped[Firm] = relationship()
    deliveries: Mapped[list[WebhookDelivery]] = relationship(
        back_populates="webhook",
        order_by="WebhookDelivery.created_at.desc()",
        lazy="dynamic",
    )


class WebhookDelivery(BaseModel):
    """Log of individual webhook delivery attempts."""

    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    # Delivery result
    status_code: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Retry tracking
    attempt: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )

    webhook: Mapped[Webhook] = relationship(back_populates="deliveries")
