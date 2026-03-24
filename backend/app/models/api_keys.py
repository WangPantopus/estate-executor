"""APIKey model — developer API keys for enterprise firms."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.firms import Firm


class APIKey(BaseModel):
    """Hashed API key associated with a firm for programmatic access."""

    __tablename__ = "api_keys"

    firm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Only the hash is stored; the raw key is returned once at creation
    key_prefix: Mapped[str] = mapped_column(
        String(12), nullable=False
    )  # "ee_live_xxxx" visible prefix for identification
    key_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True
    )

    # Permissions / scopes
    scopes: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default='["read"]'
    )  # e.g. ["read", "write", "webhooks"]

    # Rate limiting
    rate_limit_per_minute: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="60"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Tracking
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    total_requests: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    firm: Mapped[Firm] = relationship()
