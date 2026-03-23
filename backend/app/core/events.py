"""Event logging utility for immutable audit trail.

After writing to the events table, publishes to Redis pub/sub so the
Socket.IO server can broadcast real-time updates to connected clients.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActorType
from app.models.events import Event

logger = logging.getLogger(__name__)

# Map entity_type + action to Socket.IO event names
_EVENT_MAP: dict[tuple[str, str], str] = {
    ("task", "created"): "task_updated",
    ("task", "updated"): "task_updated",
    ("task", "completed"): "task_updated",
    ("task", "waived"): "task_updated",
    ("task", "assigned"): "task_updated",
    ("document", "created"): "document_uploaded",
    ("document", "uploaded"): "document_uploaded",
    ("document", "confirmed"): "document_uploaded",
    ("deadline", "created"): "deadline_updated",
    ("deadline", "updated"): "deadline_updated",
    ("communication", "created"): "communication_new",
    ("stakeholder", "created"): "stakeholder_changed",
    ("stakeholder", "updated"): "stakeholder_changed",
    ("stakeholder", "removed"): "stakeholder_changed",
}


def _serialize_uuid(value: Any) -> Any:
    """Convert UUID values to strings for JSON serialization."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _serialize_uuid(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_uuid(v) for v in value]
    return value


class EventLogger:
    """Single entry point for ALL audit logging.

    Creates Event records in the events table, then publishes to Redis
    pub/sub for real-time WebSocket broadcasting.
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
        """Log an immutable event to the audit trail and publish to real-time."""
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

        # Publish to Redis pub/sub for real-time WebSocket broadcast
        self._publish_realtime(
            matter_id=matter_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            changes=changes,
            actor_id=actor_id,
            actor_type=actor_type,
            event_id=event.id,
        )

        return event

    def _publish_realtime(
        self,
        *,
        matter_id: UUID,
        entity_type: str,
        entity_id: UUID,
        action: str,
        changes: dict[str, Any] | None,
        actor_id: UUID | None,
        actor_type: ActorType,
        event_id: UUID,
    ) -> None:
        """Publish event to Redis for Socket.IO broadcast (fire-and-forget).

        Failures are logged but never raised — real-time broadcast must not
        break the main event logging / database flow.
        """
        try:
            from app.realtime.publisher import publish_realtime_event

            # Determine the Socket.IO event name
            ws_event = _EVENT_MAP.get((entity_type, action))

            # Always emit a generic 'event_new' for the activity feed
            event_data = _serialize_uuid({
                "event_id": event_id,
                "matter_id": matter_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "changes": changes,
                "actor_id": actor_id,
                "actor_type": actor_type.value if hasattr(actor_type, "value") else actor_type,
            })

            # Emit the specific typed event (task_updated, document_uploaded, etc.)
            if ws_event:
                publish_realtime_event(
                    matter_id=str(matter_id),
                    event=ws_event,
                    data=event_data,
                )

            # Always emit event_new for the activity feed
            publish_realtime_event(
                matter_id=str(matter_id),
                event="event_new",
                data=event_data,
            )
        except Exception:
            logger.warning("realtime_publish_failed", exc_info=True)


# Module-level singleton
event_logger = EventLogger()
