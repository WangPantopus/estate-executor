"""IntegrationConnection model — OAuth credentials and sync state for integrations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import IntegrationProvider, IntegrationStatus, SyncStatus

if TYPE_CHECKING:
    from app.models.firms import Firm


class IntegrationConnection(BaseModel):
    """Represents a firm's connection to a third-party integration (e.g. Clio)."""

    __table_args__ = (
        UniqueConstraint("firm_id", "provider", name="uq_integration_firm_provider"),
        Index("ix_integration_connections_firm_id", "firm_id"),
    )

    firm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[IntegrationProvider] = mapped_column(
        Enum(IntegrationProvider, name="integration_provider", native_enum=True),
        nullable=False,
    )
    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(IntegrationStatus, name="integration_status", native_enum=True),
        nullable=False,
        server_default="disconnected",
    )

    # OAuth tokens (encrypted at rest via DB-level encryption)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # External account info
    external_account_id: Mapped[str | None] = mapped_column(String, nullable=True)
    external_account_name: Mapped[str | None] = mapped_column(String, nullable=True)

    # Sync state
    last_sync_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    last_sync_status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, name="sync_status", native_enum=True),
        nullable=False,
        server_default="idle",
    )
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_cursor: Mapped[str | None] = mapped_column(String, nullable=True)

    # Integration-specific settings (e.g. which Clio practice area to map)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    # Field mapping overrides
    field_mappings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    # ID mapping: our entity IDs → external IDs (and reverse)
    entity_map: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    connected_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    disconnected_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    firm: Mapped[Firm] = relationship()
