"""Redis pub/sub publisher for WebSocket events.

Used by the EventLogger and services to publish events that the Socket.IO
server picks up and broadcasts to connected clients.

This module works from any process (API server, Celery workers, etc.)
by publishing to Redis. The Socket.IO Redis manager handles fan-out.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_CHANNEL = "estate_executor:realtime"

# Lazy-init sync Redis client (used from both async and sync contexts)
_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def publish_realtime_event(
    *,
    matter_id: str,
    event: str,
    data: dict[str, Any],
) -> None:
    """Publish a realtime event to Redis pub/sub.

    The Socket.IO server subscribes to this channel and broadcasts to
    the appropriate matter room.

    This is a fire-and-forget operation — failures are logged but never
    raised, so they cannot break the caller's flow.
    """
    try:
        payload = json.dumps(
            {
                "matter_id": matter_id,
                "event": event,
                "data": data,
            }
        )
        _get_redis().publish(_CHANNEL, payload)
        logger.debug(
            "realtime_event_published",
            extra={"matter_id": matter_id, "event": event},
        )
    except Exception:
        logger.warning("realtime_event_publish_failed", exc_info=True)


# ---------------------------------------------------------------------------
# Event type helpers — convenience functions for common event types
# ---------------------------------------------------------------------------


def emit_task_updated(
    matter_id: str, task_id: str, changes: dict[str, Any], actor: str | None = None
) -> None:
    publish_realtime_event(
        matter_id=matter_id,
        event="task_updated",
        data={"task_id": task_id, "changes": changes, "actor": actor},
    )


def emit_document_uploaded(
    matter_id: str, document_id: str, filename: str, uploaded_by: str | None = None
) -> None:
    publish_realtime_event(
        matter_id=matter_id,
        event="document_uploaded",
        data={
            "document_id": document_id,
            "filename": filename,
            "uploaded_by": uploaded_by,
        },
    )


def emit_deadline_updated(matter_id: str, deadline_id: str, changes: dict[str, Any]) -> None:
    publish_realtime_event(
        matter_id=matter_id,
        event="deadline_updated",
        data={"deadline_id": deadline_id, "changes": changes},
    )


def emit_communication_new(
    matter_id: str, communication_id: str, comm_type: str, sender: str | None = None
) -> None:
    publish_realtime_event(
        matter_id=matter_id,
        event="communication_new",
        data={
            "communication_id": communication_id,
            "type": comm_type,
            "sender": sender,
        },
    )


def emit_stakeholder_changed(matter_id: str, stakeholder_id: str, changes: dict[str, Any]) -> None:
    publish_realtime_event(
        matter_id=matter_id,
        event="stakeholder_changed",
        data={"stakeholder_id": stakeholder_id, "changes": changes},
    )
