"""Deadline business logic service layer — CRUD, calendar view, and monitoring."""

from __future__ import annotations

import logging
import math
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.events import event_logger
from app.core.exceptions import NotFoundError
from app.models.deadlines import Deadline
from app.models.enums import ActorType, DeadlineSource, DeadlineStatus, MatterStatus
from app.models.matters import Matter
from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_deadline_or_404(
    db: AsyncSession, *, deadline_id: uuid.UUID, matter_id: uuid.UUID
) -> Deadline:
    result = await db.execute(
        select(Deadline)
        .options(selectinload(Deadline.task), selectinload(Deadline.assignee))
        .where(Deadline.id == deadline_id, Deadline.matter_id == matter_id)
    )
    deadline = result.scalar_one_or_none()
    if deadline is None:
        raise NotFoundError(detail="Deadline not found")
    return deadline


# ---------------------------------------------------------------------------
# Create deadline (manual)
# ---------------------------------------------------------------------------


async def create_deadline(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    title: str,
    description: str | None = None,
    due_date: date,
    task_id: uuid.UUID | None = None,
    assigned_to: uuid.UUID | None = None,
    reminder_config: dict | None = None,
    current_user: CurrentUser,
) -> Deadline:
    """Create a manual deadline."""
    deadline = Deadline(
        matter_id=matter_id,
        title=title,
        description=description,
        due_date=due_date,
        source=DeadlineSource.manual,
        rule=None,
        task_id=task_id,
        assigned_to=assigned_to,
        reminder_config=reminder_config or {"days_before": [30, 7, 1]},
    )
    db.add(deadline)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="deadline",
        entity_id=deadline.id,
        action="created",
        metadata={
            "title": title,
            "due_date": str(due_date),
            "source": "manual",
        },
    )

    # Reload with relationships
    return await _get_deadline_or_404(db, deadline_id=deadline.id, matter_id=matter_id)


# ---------------------------------------------------------------------------
# List deadlines
# ---------------------------------------------------------------------------


async def list_deadlines(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    status: DeadlineStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[Deadline], int]:
    """List deadlines with optional filters, sorted by due_date ascending."""
    filters = [Deadline.matter_id == matter_id]

    if status is not None:
        filters.append(Deadline.status == status)
    if date_from is not None:
        filters.append(Deadline.due_date >= date_from)
    if date_to is not None:
        filters.append(Deadline.due_date <= date_to)

    # Count
    count_q = select(func.count()).select_from(Deadline).where(*filters)
    total = (await db.execute(count_q)).scalar_one()

    # Query with task brief
    q = (
        select(Deadline)
        .options(selectinload(Deadline.task), selectinload(Deadline.assignee))
        .where(*filters)
        .order_by(Deadline.due_date.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    deadlines = list(result.scalars().unique().all())

    return deadlines, total


# ---------------------------------------------------------------------------
# Update deadline
# ---------------------------------------------------------------------------


async def update_deadline(
    db: AsyncSession,
    *,
    deadline_id: uuid.UUID,
    matter_id: uuid.UUID,
    updates: dict[str, Any],
    current_user: CurrentUser,
) -> Deadline:
    """Update a deadline. Tracks due_date changes and auto-extends status."""
    deadline = await _get_deadline_or_404(
        db, deadline_id=deadline_id, matter_id=matter_id
    )

    changes: dict[str, dict[str, Any]] = {}

    # Handle due_date change — log old/new and auto-extend
    new_due_date = updates.pop("due_date", None)
    if new_due_date is not None and new_due_date != deadline.due_date:
        changes["due_date"] = {
            "old": str(deadline.due_date),
            "new": str(new_due_date),
        }
        deadline.due_date = new_due_date

        # If extending (new date is later), auto-set status to extended
        if new_due_date > deadline.due_date or (
            "status" not in updates and deadline.status in (
                DeadlineStatus.upcoming, DeadlineStatus.missed
            )
        ):
            if "status" not in updates:
                changes["status"] = {
                    "old": deadline.status.value,
                    "new": DeadlineStatus.extended.value,
                }
                deadline.status = DeadlineStatus.extended

    # Handle explicit status change
    new_status = updates.pop("status", None)
    if new_status is not None and new_status != deadline.status:
        changes["status"] = {
            "old": deadline.status.value,
            "new": new_status.value,
        }
        deadline.status = new_status

    # Apply remaining scalar fields
    for field, value in updates.items():
        if hasattr(deadline, field):
            old_val = getattr(deadline, field)
            if old_val != value:
                changes[field] = {
                    "old": str(old_val) if old_val is not None else None,
                    "new": str(value) if value is not None else None,
                }
                setattr(deadline, field, value)

    if changes:
        await db.flush()
        await event_logger.log(
            db,
            matter_id=matter_id,
            actor_id=current_user.user_id,
            actor_type=ActorType.user,
            entity_type="deadline",
            entity_id=deadline.id,
            action="updated",
            changes=changes,
        )

    return deadline


# ---------------------------------------------------------------------------
# Calendar view
# ---------------------------------------------------------------------------


async def get_calendar(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Return deadlines grouped by month for the calendar widget.

    Returns a list of { month: "YYYY-MM", deadlines: [...] } objects,
    each deadline including task_title and assignee_name.
    """
    result = await db.execute(
        select(Deadline)
        .options(selectinload(Deadline.task), selectinload(Deadline.assignee))
        .where(Deadline.matter_id == matter_id)
        .order_by(Deadline.due_date.asc())
    )
    deadlines = result.scalars().unique().all()

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for dl in deadlines:
        month_key = dl.due_date.strftime("%Y-%m")
        grouped[month_key].append({
            "id": dl.id,
            "title": dl.title,
            "description": dl.description,
            "due_date": dl.due_date,
            "status": dl.status.value,
            "source": dl.source.value,
            "task_id": dl.task_id,
            "task_title": dl.task.title if dl.task else None,
            "assigned_to": dl.assigned_to,
            "assignee_name": dl.assignee.full_name if dl.assignee else None,
        })

    # Return sorted by month key
    return [
        {"month": month, "deadlines": items}
        for month, items in sorted(grouped.items())
    ]


# ---------------------------------------------------------------------------
# Deadline monitoring (called by Celery beat task)
# ---------------------------------------------------------------------------


async def check_deadlines(db: AsyncSession, *, today: date | None = None) -> dict[str, int]:
    """Check all active matters for overdue or reminder-due deadlines.

    Returns counts of actions taken for logging/monitoring.

    Idempotent: won't send duplicate reminders for the same day.
    """
    if today is None:
        today = date.today()

    now = datetime.now(timezone.utc)
    today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

    stats = {"missed": 0, "reminders_sent": 0}

    # Get active matters
    active_matters = await db.execute(
        select(Matter.id).where(Matter.status == MatterStatus.active)
    )
    matter_ids = [row[0] for row in active_matters.all()]

    if not matter_ids:
        return stats

    # --- 1. Mark overdue deadlines as missed ---
    overdue_q = (
        select(Deadline)
        .where(
            Deadline.matter_id.in_(matter_ids),
            Deadline.status == DeadlineStatus.upcoming,
            Deadline.due_date < today,
        )
    )
    overdue_result = await db.execute(overdue_q)
    overdue_deadlines = overdue_result.scalars().all()

    for dl in overdue_deadlines:
        dl.status = DeadlineStatus.missed
        stats["missed"] += 1

        await event_logger.log(
            db,
            matter_id=dl.matter_id,
            actor_id=None,
            actor_type=ActorType.system,
            entity_type="deadline",
            entity_id=dl.id,
            action="auto_missed",
            metadata={
                "title": dl.title,
                "due_date": str(dl.due_date),
                "detected_at": now.isoformat(),
            },
        )

    # --- 2. Send reminders for upcoming deadlines ---
    upcoming_q = (
        select(Deadline)
        .where(
            Deadline.matter_id.in_(matter_ids),
            Deadline.status == DeadlineStatus.upcoming,
            Deadline.due_date >= today,
        )
    )
    upcoming_result = await db.execute(upcoming_q)
    upcoming_deadlines = upcoming_result.scalars().all()

    for dl in upcoming_deadlines:
        reminder_config = dl.reminder_config or {"days_before": [30, 7, 1]}
        days_before_list = reminder_config.get("days_before", [30, 7, 1])
        days_until = (dl.due_date - today).days

        if days_until not in days_before_list:
            continue

        # Idempotency: skip if we already sent a reminder today
        if dl.last_reminder_sent is not None and dl.last_reminder_sent >= today_start:
            continue

        # "Send" reminder (log event — actual notification dispatch is a stub)
        dl.last_reminder_sent = now
        stats["reminders_sent"] += 1

        logger.info(
            "deadline_reminder_sent",
            extra={
                "deadline_id": str(dl.id),
                "matter_id": str(dl.matter_id),
                "title": dl.title,
                "due_date": str(dl.due_date),
                "days_until": days_until,
            },
        )

        await event_logger.log(
            db,
            matter_id=dl.matter_id,
            actor_id=None,
            actor_type=ActorType.system,
            entity_type="deadline",
            entity_id=dl.id,
            action="reminder_sent",
            metadata={
                "title": dl.title,
                "due_date": str(dl.due_date),
                "days_until": days_until,
            },
        )

    await db.flush()
    return stats
