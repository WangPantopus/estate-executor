"""Event logging utility for immutable audit trail."""

from typing import Any
from uuid import UUID


async def log_event(
    *,
    matter_id: UUID,
    actor_id: UUID | None,
    actor_type: str,
    entity_type: str,
    entity_id: UUID,
    action: str,
    changes: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Log an immutable event to the audit trail.

    TODO: Implement with database session in Prompt 003.
    """
    pass
