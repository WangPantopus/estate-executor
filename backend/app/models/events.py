import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ActorType


class Event(Base):
    """Immutable audit log. No updated_at column. matter_id is NOT a FK for partitioning."""

    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_matter_id_created_at", "matter_id", "created_at"),
        Index("ix_events_entity_type_entity_id", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_type: Mapped[ActorType] = mapped_column(
        Enum(ActorType, name="actor_type", native_enum=True),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
