"""Matter business logic service layer."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, func, or_, select

from app.core.events import event_logger
from app.core.exceptions import ConflictError, NotFoundError
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

if TYPE_CHECKING:
    import uuid
    from decimal import Decimal

    from sqlalchemy.ext.asyncio import AsyncSession

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

    # Generate tasks from templates (sync for now, async later)
    from app.services.task_generation_service import generate_tasks

    generated_tasks = await generate_tasks(db, matter_id=matter.id, actor_id=current_user.user_id)
    logger.info("Generated %d tasks for new matter %s", len(generated_tasks), matter.id)

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
    """List matters with filters.

    Non-admin firm members only see matters where they are stakeholders.
    """
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
    return list(result.scalars().all()), total  # type: ignore[arg-type]


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

    Results are cached in Redis for 60 seconds to reduce DB load on
    repeated dashboard loads.

    Returns a dict with: task_summary, asset_summary, stakeholder_count,
    upcoming_deadlines, recent_events.
    """
    from app.core.cache import get_cached_dashboard, set_cached_dashboard

    cache_key_role = (
        stakeholder_role.value if hasattr(stakeholder_role, "value") else str(stakeholder_role)
    )
    cached = get_cached_dashboard(str(matter_id), cache_key_role)
    if cached is not None:
        # The cached dict contains only serializable aggregate fields
        # (task_summary, asset_summary, stakeholder_count). Deadlines and
        # events are ORM objects and cannot be JSON-cached, so we fetch them
        # on every request. They are cheap LIMIT-5/LIMIT-10 queries.
        today = date.today()
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

        event_q = (
            select(Event)
            .where(Event.matter_id == matter_id)
            .order_by(Event.created_at.desc())
            .limit(10)
        )
        event_result = await db.execute(event_q)
        recent_events = list(event_result.scalars().all())

        if stakeholder_role == StakeholderRole.beneficiary:
            recent_events = []

        return {
            **cached,
            "upcoming_deadlines": upcoming_deadlines,
            "recent_events": recent_events,
        }

    today = date.today()

    # --- Task summary: single aggregation query ---
    task_q = select(
        func.count().label("total"),
        func.count().filter(Task.status == TaskStatus.not_started).label("not_started"),
        func.count().filter(Task.status == TaskStatus.in_progress).label("in_progress"),
        func.count().filter(Task.status == TaskStatus.blocked).label("blocked"),
        func.count().filter(Task.status == TaskStatus.complete).label("complete"),
        func.count().filter(Task.status == TaskStatus.waived).label("waived"),
        func.count()
        .filter(
            and_(
                Task.due_date < today,
                Task.status.notin_([TaskStatus.complete, TaskStatus.waived, TaskStatus.cancelled]),
            )
        )
        .label("overdue"),
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
        select(func.count()).select_from(Stakeholder).where(Stakeholder.matter_id == matter_id)
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

    result = {
        "task_summary": task_summary,
        "asset_summary": asset_summary,
        "stakeholder_count": stakeholder_count,
        "upcoming_deadlines": upcoming_deadlines,
        "recent_events": recent_events,
    }

    # Cache the serializable parts (deadlines/events are ORM objects — cache summary only)
    try:
        cacheable = {
            "task_summary": task_summary,
            "asset_summary": asset_summary,
            "stakeholder_count": stakeholder_count,
        }
        set_cached_dashboard(str(matter_id), cache_key_role, cacheable)
    except Exception:
        pass  # fail-open

    return result


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
                old_str = (
                    old_value.value  # type: ignore[union-attr]
                    if hasattr(old_value, "value")
                    else str(old_value)
                    if old_value is not None
                    else None
                )
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

        # Invalidate caches affected by matter updates
        from app.core.cache import invalidate_dashboard, invalidate_portfolio

        invalidate_dashboard(str(matter.id))
        invalidate_portfolio(str(matter.firm_id))

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
            detail=(
                f"Cannot close matter: {incomplete_count} "
                "critical task(s) are not complete or waived"
            )
        )

    matter.status = MatterStatus.closed
    matter.closed_at = datetime.now(UTC)
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
    status: MatterStatus | None = None,
    phase: MatterPhase | None = None,
    search: str | None = None,
    jurisdiction_state: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> dict[str, Any]:
    """Get portfolio view: all matters with summary stats for firm dashboard.

    Uses SQL aggregation to compute all stats in minimal queries (no N+1).
    Returns dict with: summary, items, total.
    """
    from datetime import timedelta

    from app.models.communications import Communication
    from app.models.enums import CommunicationType

    today = date.today()
    week_end = today + timedelta(days=7)

    # Build base filter
    base_filters: list[Any] = [Matter.firm_id == firm_id]
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

    # ── Summary: cross-matter aggregates ─────────────────────────────────────

    # Total active matters (unfiltered)
    active_count = (
        await db.execute(
            select(func.count())
            .select_from(Matter)
            .where(Matter.firm_id == firm_id, Matter.status == MatterStatus.active)
        )
    ).scalar_one()

    # Matters by phase (unfiltered, active only)
    phase_q = (
        select(Matter.phase, func.count().label("cnt"))
        .where(Matter.firm_id == firm_id, Matter.status == MatterStatus.active)
        .group_by(Matter.phase)
    )
    matters_by_phase = {
        row.phase.value if hasattr(row.phase, "value") else row.phase: row.cnt
        for row in (await db.execute(phase_q)).all()
    }

    # All active matter IDs for cross-matter aggregation
    all_active_ids_q = select(Matter.id).where(
        Matter.firm_id == firm_id, Matter.status == MatterStatus.active
    )
    all_active_ids = [row[0] for row in (await db.execute(all_active_ids_q)).all()]

    total_overdue_tasks = 0
    approaching_deadlines_this_week = 0

    if all_active_ids:
        # Total overdue tasks across all matters
        total_overdue_tasks = (
            await db.execute(
                select(func.count())
                .select_from(Task)
                .where(
                    Task.matter_id.in_(all_active_ids),
                    Task.due_date < today,
                    Task.status.notin_(
                        [TaskStatus.complete, TaskStatus.waived, TaskStatus.cancelled]
                    ),
                    Task.due_date.isnot(None),
                )
            )
        ).scalar_one()

        # Deadlines approaching this week
        approaching_deadlines_this_week = (
            await db.execute(
                select(func.count())
                .select_from(Deadline)
                .where(
                    Deadline.matter_id.in_(all_active_ids),
                    Deadline.status == DeadlineStatus.upcoming,
                    Deadline.due_date >= today,
                    Deadline.due_date <= week_end,
                )
            )
        ).scalar_one()

    summary = {
        "total_active_matters": active_count,
        "total_overdue_tasks": total_overdue_tasks,
        "approaching_deadlines_this_week": approaching_deadlines_this_week,
        "matters_by_phase": matters_by_phase,
    }

    # ── Filtered matters with pagination ─────────────────────────────────────

    count_q = select(func.count()).select_from(Matter).where(*base_filters)
    total = (await db.execute(count_q)).scalar_one()

    matters_q = (
        select(Matter)
        .where(*base_filters)
        .order_by(Matter.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    matters = list((await db.execute(matters_q)).scalars().all())

    if not matters:
        return {"summary": summary, "items": [], "total": total}

    matter_ids = [m.id for m in matters]

    # ── Per-matter aggregation queries (all in batch) ────────────────────────

    # Task stats per matter (single query)
    task_stats_q = (
        select(
            Task.matter_id,
            func.count().label("total_count"),
            func.count().filter(Task.status == TaskStatus.complete).label("complete_count"),
            func.count()
            .filter(
                Task.status.notin_([TaskStatus.complete, TaskStatus.waived, TaskStatus.cancelled])
            )
            .label("open_count"),
            func.count()
            .filter(
                and_(
                    Task.due_date < today,
                    Task.due_date.isnot(None),
                    Task.status.notin_(
                        [TaskStatus.complete, TaskStatus.waived, TaskStatus.cancelled]
                    ),
                )
            )
            .label("overdue_count"),
            func.min(Task.updated_at)
            .filter(Task.status == TaskStatus.blocked)
            .label("oldest_blocked_at"),
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
        row.matter_id: row.next_due_date for row in (await db.execute(next_deadline_q)).all()
    }

    # Approaching deadlines count per matter (this week)
    approaching_dl_q = (
        select(
            Deadline.matter_id,
            func.count().label("cnt"),
        )
        .where(
            Deadline.matter_id.in_(matter_ids),
            Deadline.status == DeadlineStatus.upcoming,
            Deadline.due_date >= today,
            Deadline.due_date <= week_end,
        )
        .group_by(Deadline.matter_id)
    )
    approaching_dl = {row.matter_id: row.cnt for row in (await db.execute(approaching_dl_q)).all()}

    # Dispute flags per matter (unresolved)
    dispute_q = (
        select(Communication.matter_id)
        .where(
            Communication.matter_id.in_(matter_ids),
            Communication.type == CommunicationType.dispute_flag,
        )
        .group_by(Communication.matter_id)
    )
    matters_with_disputes = {row[0] for row in (await db.execute(dispute_q)).all()}

    # ── Build response items with risk level ─────────────────────────────────

    from datetime import datetime

    portfolio_items = []
    for matter in matters:
        stats = task_stats.get(matter.id)
        overdue_count = stats.overdue_count if stats else 0
        open_count = stats.open_count if stats else 0
        total_count = stats.total_count if stats else 0
        complete_count = stats.complete_count if stats else 0
        has_dispute = matter.id in matters_with_disputes

        # Compute oldest blocked task days
        oldest_blocked_days: int | None = None
        if stats and stats.oldest_blocked_at:
            now_utc = datetime.now(UTC)
            blocked_at = stats.oldest_blocked_at
            if blocked_at.tzinfo is None:
                blocked_at = blocked_at.replace(tzinfo=UTC)
            oldest_blocked_days = (now_utc - blocked_at).days

        # Compute risk level
        risk_level = _compute_risk_level(
            overdue_count=overdue_count,
            has_dispute=has_dispute,
            oldest_blocked_days=oldest_blocked_days,
        )

        portfolio_items.append(
            {
                "matter": matter,
                "total_task_count": total_count,
                "complete_task_count": complete_count,
                "open_task_count": open_count,
                "overdue_task_count": overdue_count,
                "approaching_deadline_count": approaching_dl.get(matter.id, 0),
                "next_deadline": next_deadlines.get(matter.id),
                "has_dispute": has_dispute,
                "oldest_blocked_task_days": oldest_blocked_days,
                "risk_level": risk_level,
            }
        )

    # Sort by risk level (red first, then amber, then green)
    risk_order = {"red": 0, "amber": 1, "green": 2}
    portfolio_items.sort(key=lambda x: risk_order.get(x["risk_level"], 2))

    return {"summary": summary, "items": portfolio_items, "total": total}


def _compute_risk_level(
    *,
    overdue_count: int,
    has_dispute: bool,
    oldest_blocked_days: int | None,
) -> str:
    """Compute a risk level for a matter based on its stats.

    - red: any overdue tasks, or dispute flag, or blocked > 14 days
    - amber: blocked > 7 days, or approaching deadline this week
    - green: everything on track
    """
    if overdue_count > 0 or has_dispute:
        return "red"
    if oldest_blocked_days is not None and oldest_blocked_days > 14:
        return "red"
    if oldest_blocked_days is not None and oldest_blocked_days > 7:
        return "amber"
    return "green"
