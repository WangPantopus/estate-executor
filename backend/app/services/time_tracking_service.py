"""Time tracking business logic — CRUD and reporting."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import selectinload

from app.core.events import event_logger
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.enums import ActorType
from app.models.stakeholders import Stakeholder
from app.models.tasks import Task
from app.models.time_entries import TimeEntry

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_entry_or_404(
    db: AsyncSession, *, entry_id: uuid.UUID, matter_id: uuid.UUID
) -> TimeEntry:
    result = await db.execute(
        select(TimeEntry)
        .options(selectinload(TimeEntry.task), selectinload(TimeEntry.stakeholder))
        .where(TimeEntry.id == entry_id, TimeEntry.matter_id == matter_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise NotFoundError(detail="Time entry not found")
    return entry


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def create_time_entry(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    stakeholder: Stakeholder,
    task_id: uuid.UUID | None = None,
    hours: int,
    minutes: int,
    description: str,
    entry_date: Any,
    billable: bool = True,
    current_user: CurrentUser,
) -> TimeEntry:
    """Create a time entry for the current stakeholder."""
    entry = TimeEntry(
        matter_id=matter_id,
        stakeholder_id=stakeholder.id,
        task_id=task_id,
        hours=hours,
        minutes=minutes,
        description=description,
        entry_date=entry_date,
        billable=billable,
    )
    db.add(entry)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="time_entry",
        entity_id=entry.id,
        action="created",
        metadata={
            "hours": hours,
            "minutes": minutes,
            "task_id": str(task_id) if task_id else None,
            "billable": billable,
        },
    )

    return await _get_entry_or_404(db, entry_id=entry.id, matter_id=matter_id)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


async def list_time_entries(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    task_id: uuid.UUID | None = None,
    stakeholder_id: uuid.UUID | None = None,
    billable: bool | None = None,
    date_from: Any = None,
    date_to: Any = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[TimeEntry], int]:
    """List time entries with filters and pagination."""
    filters: list[Any] = [TimeEntry.matter_id == matter_id]

    if task_id is not None:
        filters.append(TimeEntry.task_id == task_id)
    if stakeholder_id is not None:
        filters.append(TimeEntry.stakeholder_id == stakeholder_id)
    if billable is not None:
        filters.append(TimeEntry.billable == billable)
    if date_from is not None:
        filters.append(TimeEntry.entry_date >= date_from)
    if date_to is not None:
        filters.append(TimeEntry.entry_date <= date_to)

    count_q = select(func.count()).select_from(TimeEntry).where(*filters)
    total = (await db.execute(count_q)).scalar_one()

    q = (
        select(TimeEntry)
        .options(selectinload(TimeEntry.task), selectinload(TimeEntry.stakeholder))
        .where(*filters)
        .order_by(TimeEntry.entry_date.desc(), TimeEntry.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    entries = list(result.scalars().unique().all())

    return entries, total


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def update_time_entry(
    db: AsyncSession,
    *,
    entry_id: uuid.UUID,
    matter_id: uuid.UUID,
    stakeholder: Stakeholder,
    current_user: CurrentUser,
    **fields: Any,
) -> TimeEntry:
    """Update a time entry. Only the author can update their own entries."""
    entry = await _get_entry_or_404(db, entry_id=entry_id, matter_id=matter_id)

    if entry.stakeholder_id != stakeholder.id:
        raise PermissionDeniedError(detail="Can only edit your own time entries")

    changes = {}
    for field, value in fields.items():
        if value is not None and hasattr(entry, field):
            old = getattr(entry, field)
            if old != value:
                changes[field] = {"old": str(old), "new": str(value)}
                setattr(entry, field, value)

    if changes:
        await db.flush()
        await event_logger.log(
            db,
            matter_id=matter_id,
            actor_id=current_user.user_id,
            actor_type=ActorType.user,
            entity_type="time_entry",
            entity_id=entry.id,
            action="updated",
            changes=changes,
        )

    return await _get_entry_or_404(db, entry_id=entry_id, matter_id=matter_id)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


async def delete_time_entry(
    db: AsyncSession,
    *,
    entry_id: uuid.UUID,
    matter_id: uuid.UUID,
    stakeholder: Stakeholder,
    current_user: CurrentUser,
) -> None:
    """Delete a time entry. Only the author can delete their own entries."""
    entry = await _get_entry_or_404(db, entry_id=entry_id, matter_id=matter_id)

    if entry.stakeholder_id != stakeholder.id:
        raise PermissionDeniedError(detail="Can only delete your own time entries")

    await db.delete(entry)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="time_entry",
        entity_id=entry_id,
        action="deleted",
    )


# ---------------------------------------------------------------------------
# Summary / reporting
# ---------------------------------------------------------------------------


async def get_time_summary(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
) -> dict[str, Any]:
    """Compute time tracking summary for a matter."""
    # Total time
    totals_q = select(
        func.coalesce(func.sum(TimeEntry.hours), 0).label("total_hours"),
        func.coalesce(func.sum(TimeEntry.minutes), 0).label("total_minutes"),
        func.coalesce(
            func.sum(
                case(
                    (TimeEntry.billable == True, TimeEntry.hours * 60 + TimeEntry.minutes),  # noqa: E712
                    else_=0,
                )
            ),
            0,
        ).label("billable_minutes"),
        func.coalesce(
            func.sum(
                case(
                    (TimeEntry.billable == False, TimeEntry.hours * 60 + TimeEntry.minutes),  # noqa: E712
                    else_=0,
                )
            ),
            0,
        ).label("non_billable_minutes"),
    ).where(TimeEntry.matter_id == matter_id)

    row = (await db.execute(totals_q)).one()
    raw_hours = int(row.total_hours)
    raw_minutes = int(row.total_minutes)
    total_mins = raw_hours * 60 + raw_minutes
    billable_mins = int(row.billable_minutes)
    non_billable_mins = int(row.non_billable_minutes)

    # By stakeholder
    by_stakeholder_q = (
        select(
            Stakeholder.id,
            Stakeholder.full_name,
            func.coalesce(func.sum(TimeEntry.hours * 60 + TimeEntry.minutes), 0).label(
                "total_minutes"
            ),
        )
        .join(TimeEntry, TimeEntry.stakeholder_id == Stakeholder.id)
        .where(TimeEntry.matter_id == matter_id)
        .group_by(Stakeholder.id, Stakeholder.full_name)
        .order_by(func.sum(TimeEntry.hours * 60 + TimeEntry.minutes).desc())
    )
    by_stakeholder = [
        {
            "stakeholder_id": str(r[0]),
            "name": r[1],
            "total_minutes": int(r[2]),
            "decimal_hours": round(int(r[2]) / 60, 2),
        }
        for r in (await db.execute(by_stakeholder_q)).all()
    ]

    # By task
    by_task_q = (
        select(
            Task.id,
            Task.title,
            func.coalesce(func.sum(TimeEntry.hours * 60 + TimeEntry.minutes), 0).label(
                "total_minutes"
            ),
        )
        .join(TimeEntry, TimeEntry.task_id == Task.id)
        .where(TimeEntry.matter_id == matter_id)
        .group_by(Task.id, Task.title)
        .order_by(func.sum(TimeEntry.hours * 60 + TimeEntry.minutes).desc())
    )
    by_task = [
        {
            "task_id": str(r[0]),
            "title": r[1],
            "total_minutes": int(r[2]),
            "decimal_hours": round(int(r[2]) / 60, 2),
        }
        for r in (await db.execute(by_task_q)).all()
    ]

    return {
        "total_hours": total_mins // 60,
        "total_minutes": total_mins % 60,
        "total_decimal_hours": round(total_mins / 60, 2),
        "billable_hours": round(billable_mins / 60, 2),
        "non_billable_hours": round(non_billable_mins / 60, 2),
        "by_stakeholder": by_stakeholder,
        "by_task": by_task,
    }
