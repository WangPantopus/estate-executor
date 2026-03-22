"""Matter business logic service layer."""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import event_logger
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models.assets import Asset
from app.models.deadlines import Deadline
from app.models.enums import (
    ActorType,
    DeadlineStatus,
    FirmRole,
    InviteStatus,
    MatterPhase,
    MatterStatus,
    StakeholderRole,
    TaskPriority,
    TaskStatus,
)
from app.models.events import Event
from app.models.firm_memberships import FirmMembership
from app.models.matters import Matter
from app.models.stakeholders import Stakeholder
from app.models.tasks import Task
from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Create matter
# ---------------------------------------------------------------------------


async def create_matter(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    title: str,
    estate_type: str,
    jurisdiction_state: str,
    decedent_name: str,
    date_of_death: date | None = None,
    date_of_incapacity: date | None = None,
    estimated_value: Decimal | None = None,
    current_user: CurrentUser,
) -> Matter:
    """Create a new matter and add the creator as matter_admin stakeholder."""
    matter = Matter(
        firm_id=firm_id,
        title=title,
        estate_type=estate_type,
        jurisdiction_state=jurisdiction_state,
        decedent_name=decedent_name,
        date_of_death=date_of_death,
        date_of_incapacity=date_of_incapacity,
        estimated_value=estimated_value,
    )
    db.add(matter)
    await db.flush()

    # Add creator as matter_admin stakeholder
    stakeholder = Stakeholder(
        matter_id=matter.id,
        user_id=current_user.user_id,
        email=current_user.email,
        full_name=current_user.email.split("@")[0],
        role=StakeholderRole.matter_admin,
        invite_status=InviteStatus.accepted,
    )
    db.add(stakeholder)
    await db.flush()

    # TODO: trigger task generation (sync for now, async later)

    await event_logger.log(
        db,
        matter_id=matter.id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="matter",
        entity_id=matter.id,
        action="created",
        metadata={
            "title": title,
            "estate_type": estate_type,
            "jurisdiction_state": jurisdiction_state,
        },
    )

    return matter


# ---------------------------------------------------------------------------
# List matters
# ---------------------------------------------------------------------------


async def list_matters(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
    status: MatterStatus | None = None,
    phase: MatterPhase | None = None,
    search: str | None = None,
    jurisdiction_state: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[Matter], int]:
    """List matters with filters. Non-admin firm members only see matters where they are stakeholders."""
    # Check if user is a firm admin/owner
    membership_q = select(FirmMembership).where(
        FirmMembership.firm_id == firm_id,
        FirmMembership.user_id == current_user.user_id,
    )
    result = await db.execute(membership_q)
    membership = result.scalar_one_or_none()

    is_firm_admin = membership is not None and membership.firm_role in (
        FirmRole.owner,
        FirmRole.admin,
    )

    # Base query
    base_filters = [Matter.firm_id == firm_id]

    if status is not None:
        base_filters.append(Matter.status == status)
    if phase is not None:
        base_filters.append(Matter.phase == phase)
    if jurisdiction_state is not None:
        base_filters.append(Matter.jurisdiction_state == jurisdiction_state)
    if search:
        search_term = f"%{search}%"
        base_filters.append(
            or_(
                Matter.title.ilike(search_term),
                Matter.decedent_name.ilike(search_term),
            )
        )

    if is_firm_admin:
        # Firm admins see all matters
        count_q = select(func.count()).select_from(Matter).where(*base_filters)
        q = select(Matter).where(*base_filters)
    else:
        # Non-admins only see matters where they are stakeholders
        count_q = (
            select(func.count())
            .select_from(Matter)
            .join(Stakeholder, Stakeholder.matter_id == Matter.id)
            .where(*base_filters, Stakeholder.user_id == current_user.user_id)
        )
        q = (
            select(Matter)
            .join(Stakeholder, Stakeholder.matter_id == Matter.id)
            .where(*base_filters, Stakeholder.user_id == current_user.user_id)
        )

    total = (await db.execute(count_q)).scalar_one()

    q = q.order_by(Matter.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    return list(result.scalars().all()), total


# ---------------------------------------------------------------------------
# Get matter (single)
# ---------------------------------------------------------------------------


async def get_matter(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
) -> Matter:
    """Get a matter by ID. Raises NotFoundError if not found."""
    result = await db.execute(select(Matter).where(Matter.id == matter_id))
    matter = result.scalar_one_or_none()
    if matter is None:
        raise NotFoundError(detail="Matter not found")
    return matter


# ---------------------------------------------------------------------------
# Dashboard aggregation
# ---------------------------------------------------------------------------


async def get_dashboard(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    stakeholder_role: StakeholderRole,
) -> dict[str, Any]:
    """Build dashboard data using SQL aggregation queries.

    Returns a dict with: task_summary, asset_summary, stakeholder_count,
    upcoming_deadlines, recent_events.
    """
    today = date.today()

    # --- Task summary: single aggregation query ---
    task_q = select(
        func.count().label("total"),
        func.count().filter(Task.status == TaskStatus.not_started).label("not_started"),
        func.count().filter(Task.status == TaskStatus.in_progress).label("in_progress"),
        func.count().filter(Task.status == TaskStatus.blocked).label("blocked"),
        func.count().filter(Task.status == TaskStatus.complete).label("complete"),
        func.count().filter(Task.status == TaskStatus.waived).label("waived"),
        func.count().filter(
            and_(
                Task.due_date < today,
                Task.status.notin_([TaskStatus.complete, TaskStatus.waived, TaskStatus.cancelled]),
            )
        ).label("overdue"),
    ).where(Task.matter_id == matter_id)

    task_result = (await db.execute(task_q)).one()
    total_tasks = task_result.total or 0
    complete_tasks = task_result.complete or 0
    completion_pct = round((complete_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0.0

    task_summary = {
        "total": total_tasks,
        "not_started": task_result.not_started or 0,
        "in_progress": task_result.in_progress or 0,
        "blocked": task_result.blocked or 0,
        "complete": complete_tasks,
        "waived": task_result.waived or 0,
        "overdue": task_result.overdue or 0,
        "completion_percentage": completion_pct,
    }

    # --- Asset summary: single aggregation query ---
    asset_q = select(
        func.count().label("total_count"),
        func.sum(Asset.current_estimated_value).label("total_value"),
    ).where(Asset.matter_id == matter_id)

    asset_result = (await db.execute(asset_q)).one()

    # Asset counts by type
    by_type_q = (
        select(Asset.asset_type, func.count().label("cnt"))
        .where(Asset.matter_id == matter_id)
        .group_by(Asset.asset_type)
    )
    by_type_rows = (await db.execute(by_type_q)).all()
    by_type = {row.asset_type.value: row.cnt for row in by_type_rows}

    # Asset counts by status
    by_status_q = (
        select(Asset.status, func.count().label("cnt"))
        .where(Asset.matter_id == matter_id)
        .group_by(Asset.status)
    )
    by_status_rows = (await db.execute(by_status_q)).all()
    by_status = {row.status.value: row.cnt for row in by_status_rows}

    asset_summary = {
        "total_count": asset_result.total_count or 0,
        "total_estimated_value": asset_result.total_value,
        "by_type": by_type,
        "by_status": by_status,
    }

    # --- Stakeholder count ---
    stakeholder_count_q = (
        select(func.count())
        .select_from(Stakeholder)
        .where(Stakeholder.matter_id == matter_id)
    )
    stakeholder_count = (await db.execute(stakeholder_count_q)).scalar_one()

    # --- Upcoming deadlines (next 5) ---
    deadline_q = (
        select(Deadline)
        .where(
            Deadline.matter_id == matter_id,
            Deadline.status == DeadlineStatus.upcoming,
            Deadline.due_date >= today,
        )
        .order_by(Deadline.due_date)
        .limit(5)
    )
    deadline_result = await db.execute(deadline_q)
    upcoming_deadlines = list(deadline_result.scalars().all())

    # --- Recent events (last 10) ---
    event_q = (
        select(Event)
        .where(Event.matter_id == matter_id)
        .order_by(Event.created_at.desc())
        .limit(10)
    )
    event_result = await db.execute(event_q)
    recent_events = list(event_result.scalars().all())

    # Beneficiaries get reduced dashboard
    if stakeholder_role == StakeholderRole.beneficiary:
        asset_summary = {
            "total_count": asset_summary["total_count"],
            "total_estimated_value": None,
            "by_type": {},
            "by_status": {},
        }
        recent_events = []

    return {
        "task_summary": task_summary,
        "asset_summary": asset_summary,
        "stakeholder_count": stakeholder_count,
        "upcoming_deadlines": upcoming_deadlines,
        "recent_events": recent_events,
    }


# ---------------------------------------------------------------------------
# Update matter
# ---------------------------------------------------------------------------


async def update_matter(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    updates: dict[str, Any],
    current_user: CurrentUser,
) -> Matter:
    """Update a matter. Returns updated matter."""
    matter = await get_matter(db, matter_id=matter_id)

    changes: dict[str, Any] = {}
    for field, value in updates.items():
        if value is not None:
            old_value = getattr(matter, field, None)
            if old_value != value:
                old_str = old_value.value if hasattr(old_value, "value") else str(old_value) if old_value is not None else None
                new_str = value.value if hasattr(value, "value") else str(value)
                changes[field] = {"old": old_str, "new": new_str}
                setattr(matter, field, value)

    if changes:
        await db.flush()
        await event_logger.log(
            db,
            matter_id=matter.id,
            actor_id=current_user.user_id,
            actor_type=ActorType.user,
            entity_type="matter",
            entity_id=matter.id,
            action="updated",
            changes=changes,
        )

    return matter


# ---------------------------------------------------------------------------
# Close matter
# ---------------------------------------------------------------------------


async def close_matter(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    current_user: CurrentUser,
) -> Matter:
    """Close a matter. Validates all critical tasks are complete or waived."""
    matter = await get_matter(db, matter_id=matter_id)

    if matter.status == MatterStatus.closed:
        raise ConflictError(detail="Matter is already closed")

    # Check for incomplete critical tasks
    incomplete_critical_q = (
        select(func.count())
        .select_from(Task)
        .where(
            Task.matter_id == matter_id,
            Task.priority == TaskPriority.critical,
            Task.status.notin_([TaskStatus.complete, TaskStatus.waived, TaskStatus.cancelled]),
        )
    )
    incomplete_count = (await db.execute(incomplete_critical_q)).scalar_one()

    if incomplete_count > 0:
        raise ConflictError(
            detail=f"Cannot close matter: {incomplete_count} critical task(s) are not complete or waived"
        )

    matter.status = MatterStatus.closed
    matter.closed_at = datetime.now(timezone.utc)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter.id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="matter",
        entity_id=matter.id,
        action="closed",
    )

    return matter


# ---------------------------------------------------------------------------
# Portfolio view (firm-level summary)
# ---------------------------------------------------------------------------


async def get_portfolio(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """Get portfolio view: all matters with summary stats for firm dashboard."""
    today = date.today()

    # Count total matters
    count_q = (
        select(func.count()).select_from(Matter).where(Matter.firm_id == firm_id)
    )
    total = (await db.execute(count_q)).scalar_one()

    # Get matters with pagination
    matters_q = (
        select(Matter)
        .where(Matter.firm_id == firm_id)
        .order_by(Matter.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    matters_result = await db.execute(matters_q)
    matters = list(matters_result.scalars().all())

    if not matters:
        return [], total

    matter_ids = [m.id for m in matters]

    # Aggregate task stats per matter in one query
    task_stats_q = (
        select(
            Task.matter_id,
            func.count().filter(
                Task.status.notin_([TaskStatus.complete, TaskStatus.waived, TaskStatus.cancelled])
            ).label("open_count"),
            func.count().filter(
                and_(
                    Task.due_date < today,
                    Task.status.notin_([TaskStatus.complete, TaskStatus.waived, TaskStatus.cancelled]),
                )
            ).label("overdue_count"),
        )
        .where(Task.matter_id.in_(matter_ids))
        .group_by(Task.matter_id)
    )
    task_stats = {row.matter_id: row for row in (await db.execute(task_stats_q)).all()}

    # Next deadline per matter
    next_deadline_q = (
        select(
            Deadline.matter_id,
            func.min(Deadline.due_date).label("next_due_date"),
        )
        .where(
            Deadline.matter_id.in_(matter_ids),
            Deadline.status == DeadlineStatus.upcoming,
            Deadline.due_date >= today,
        )
        .group_by(Deadline.matter_id)
    )
    next_deadlines = {
        row.matter_id: row.next_due_date
        for row in (await db.execute(next_deadline_q)).all()
    }

    # Build response
    portfolio_items = []
    for matter in matters:
        stats = task_stats.get(matter.id)
        portfolio_items.append({
            "matter": matter,
            "open_task_count": stats.open_count if stats else 0,
            "overdue_task_count": stats.overdue_count if stats else 0,
            "next_deadline": next_deadlines.get(matter.id),
        })

    return portfolio_items, total
