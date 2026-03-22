"""Event logging utility for immutable audit trail."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActorType
from app.models.events import Event

logger = logging.getLogger(__name__)


class EventLogger:
    """Single entry point for ALL audit logging.

    Creates Event records in the events table.
    """

    async def log(
        self,
        db: AsyncSession,
        *,
        matter_id: UUID,
        actor_id: UUID | None,
        actor_type: ActorType,
        entity_type: str,
        entity_id: UUID,
        action: str,
        changes: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        request: Request | None = None,
    ) -> Event:
        """Log an immutable event to the audit trail."""
        ip_address: str | None = None
        user_agent: str | None = None

        if request is not None:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")

        event = Event(
            matter_id=matter_id,
            actor_id=actor_id,
            actor_type=actor_type,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            changes=changes,
            metadata_=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(event)
        await db.flush()

        logger.info(
            "event_logged",
            extra={
                "event_id": str(event.id),
                "matter_id": str(matter_id),
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "action": action,
            },
        )

        return event


# Module-level singleton
event_logger = EventLogger()
