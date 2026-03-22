"""Event service layer — READ-ONLY queries and CSV export.

Events are ONLY created through the EventLogger utility (app.core.events).
This service deliberately provides no create/update/delete operations.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.events import Event
from app.models.stakeholders import Stakeholder

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Actor name lookup (batch for efficiency)
# ---------------------------------------------------------------------------


async def _load_actor_names(
    db: AsyncSession, *, actor_ids: set[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """Load stakeholder full_name for a set of actor user_ids."""
    if not actor_ids:
        return {}
    result = await db.execute(
        select(Stakeholder.user_id, Stakeholder.full_name).where(
            Stakeholder.user_id.in_(actor_ids)
        )
    )
    # A user may be a stakeholder on multiple matters; just pick any name
    names: dict[uuid.UUID, str] = {}
    for user_id, full_name in result.all():
        if user_id is not None and user_id not in names:
            names[user_id] = full_name
    return names


# ---------------------------------------------------------------------------
# List events (cursor-based pagination)
# ---------------------------------------------------------------------------


async def list_events(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    action: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    cursor: str | None = None,
    per_page: int = 50,
) -> tuple[list[Event], dict[uuid.UUID, str], str | None]:
    """Query events with filters, cursor-based pagination, newest first.

    Returns (events, actor_names_map, next_cursor).
    Cursor is the created_at ISO timestamp of the last event in the page.
    """
    filters: list[Any] = [Event.matter_id == matter_id]

    if entity_type is not None:
        filters.append(Event.entity_type == entity_type)
    if entity_id is not None:
        filters.append(Event.entity_id == entity_id)
    if actor_id is not None:
        filters.append(Event.actor_id == actor_id)
    if action is not None:
        filters.append(Event.action == action)
    if date_from is not None:
        filters.append(Event.created_at >= datetime(date_from.year, date_from.month, date_from.day))
    if date_to is not None:
        # Include the full day by using start of the next day
        next_day = date_to + timedelta(days=1)
        filters.append(Event.created_at < datetime(next_day.year, next_day.month, next_day.day))

    # Cursor: resume after a specific (created_at, id) pair to avoid skipping
    # events with identical timestamps. Format: "ISO_TIMESTAMP|UUID"
    if cursor is not None:
        parts = cursor.split("|", 1)
        cursor_dt = datetime.fromisoformat(parts[0])
        if len(parts) == 2:
            cursor_id = uuid.UUID(parts[1])
            # Events with same timestamp but earlier id, OR earlier timestamp
            filters.append(
                or_(
                    Event.created_at < cursor_dt,
                    (Event.created_at == cursor_dt) & (Event.id < cursor_id),
                )
            )
        else:
            filters.append(Event.created_at < cursor_dt)

    q = (
        select(Event)
        .where(*filters)
        .order_by(Event.created_at.desc(), Event.id.desc())
        .limit(per_page + 1)  # fetch one extra to detect has_more
    )
    result = await db.execute(q)
    events = list(result.scalars().all())

    # Determine if there are more pages
    has_more = len(events) > per_page
    if has_more:
        events = events[:per_page]

    next_cursor = None
    if has_more and events:
        last = events[-1]
        next_cursor = f"{last.created_at.isoformat()}|{last.id}"

    # Batch-load actor names
    actor_ids = {e.actor_id for e in events if e.actor_id is not None}
    actor_names = await _load_actor_names(db, actor_ids=actor_ids)

    return events, actor_names, next_cursor


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


def _summarize_changes(changes: dict | None) -> str:
    """Create a human-readable summary of changes dict."""
    if not changes:
        return ""
    parts = []
    for field, diff in changes.items():
        if isinstance(diff, dict) and "old" in diff and "new" in diff:
            parts.append(f"{field}: {diff['old']} → {diff['new']}")
        else:
            parts.append(f"{field}: {json.dumps(diff)}")
    return "; ".join(parts)


async def export_events_csv(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
) -> str:
    """Export all events for a matter as CSV string.

    Columns: timestamp, actor, entity_type, entity_id, action, changes_summary
    """
    # Fetch all events for the matter, oldest first for chronological CSV
    result = await db.execute(
        select(Event)
        .where(Event.matter_id == matter_id)
        .order_by(Event.created_at.asc())
    )
    events = list(result.scalars().all())

    # Batch-load actor names
    actor_ids = {e.actor_id for e in events if e.actor_id is not None}
    actor_names = await _load_actor_names(db, actor_ids=actor_ids)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "actor", "entity_type", "entity_id", "action", "changes_summary"])

    for event in events:
        actor_name = actor_names.get(event.actor_id, event.actor_type.value) if event.actor_id else event.actor_type.value
        writer.writerow([
            event.created_at.isoformat(),
            actor_name,
            event.entity_type,
            str(event.entity_id),
            event.action,
            _summarize_changes(event.changes),
        ])

    return output.getvalue()
