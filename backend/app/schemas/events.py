"""Event (audit log) schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ActorType


class EventResponse(BaseModel):
    """Schema for event/audit log response."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    matter_id: UUID
    actor_id: UUID | None
    actor_type: ActorType
    actor_name: str | None = None
    entity_type: str
    entity_id: UUID
    action: str
    changes: dict[str, Any] | None
    metadata: dict[str, Any] | None
    created_at: datetime


class CursorMeta(BaseModel):
    """Cursor-based pagination metadata for large event volumes."""

    model_config = ConfigDict(strict=True)

    has_more: bool
    next_cursor: str | None = None
    per_page: int


class EventListResponse(BaseModel):
    """Cursor-paginated list of events."""

    model_config = ConfigDict(strict=True)

    data: list[EventResponse]
    meta: CursorMeta
