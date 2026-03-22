"""Event (audit log) schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ActorType

from .common import PaginationMeta


class EventResponse(BaseModel):
    """Schema for event/audit log response."""

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "matter_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "actor_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                    "actor_type": "user",
                    "entity_type": "task",
                    "entity_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
                    "action": "updated",
                    "changes": {
                        "status": {"old": "not_started", "new": "in_progress"}
                    },
                    "metadata": {},
                    "created_at": "2025-01-15T10:30:00Z",
                }
            ]
        },
    )

    id: UUID
    matter_id: UUID
    actor_id: UUID | None
    actor_type: ActorType
    entity_type: str
    entity_id: UUID
    action: str
    changes: dict | None
    metadata: dict | None
    created_at: datetime


class EventListResponse(BaseModel):
    """Paginated list of events."""

    model_config = ConfigDict(strict=True)

    data: list[EventResponse]
    meta: PaginationMeta
