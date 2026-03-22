"""Task generation service — creates tasks, dependencies, and deadlines from templates."""

from __future__ import annotations

import calendar
import logging
import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import event_logger
from app.models.deadlines import Deadline
from app.models.enums import ActorType, DeadlineSource, TaskPhase, TaskPriority
from app.models.matters import Matter
from app.models.task_dependencies import TaskDependency
from app.models.tasks import Task
from app.services.template_registry import template_registry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Date calculation helpers
# ---------------------------------------------------------------------------


def _add_months(d: date, months: int) -> date:
    """Add *months* to a date, clamping to the last day of the target month."""
    total_months = d.month + months - 1
    year = d.year + total_months // 12
    month = total_months % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _resolve_due_date(
    rule: dict[str, Any] | None,
    date_of_death: date | None,
    matter_created: date,
) -> date | None:
    """Calculate an absolute due date from a due_date_rule dict.

    Returns None if the rule is empty or the required reference date is missing.
    """
    if not rule:
        return None

    relative_to = rule.get("relative_to")
    if relative_to == "date_of_death":
        base = date_of_death
    elif relative_to == "matter_created":
        base = matter_created
    else:
        return None

    if base is None:
        return None

    offset_days = rule.get("offset_days")
    offset_months = rule.get("offset_months")

    if offset_months:
        return _add_months(base, offset_months)
    if offset_days:
        return base + timedelta(days=offset_days)

    return None


# ---------------------------------------------------------------------------
# Phase sort order mapping
# ---------------------------------------------------------------------------

# Gives each TaskPhase a base sort_order so tasks are ordered by phase first.
_PHASE_BASE_ORDER: dict[str, int] = {
    "immediate": 0,
    "asset_inventory": 1000,
    "notification": 2000,
    "probate_filing": 3000,
    "tax": 4000,
    "transfer_distribution": 5000,
    "family_communication": 6000,
    "closing": 7000,
    "custom": 8000,
}


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------


async def _fetch_matter(db: AsyncSession, matter_id: uuid.UUID) -> Matter:
    """Fetch a matter by ID or raise."""
    from app.core.exceptions import NotFoundError

    result = await db.execute(select(Matter).where(Matter.id == matter_id))
    matter = result.scalar_one_or_none()
    if matter is None:
        raise NotFoundError(detail="Matter not found")
    return matter


def _get_matter_flags(matter: Matter) -> list[str]:
    """Extract flags from matter settings for template condition evaluation."""
    flags: list[str] = []
    settings = matter.settings or {}

    # High-value estate flag (federal estate tax threshold ~$13M)
    if matter.estimated_value and matter.estimated_value > 12_920_000:
        flags.append("high_value_estate")

    # User-defined flags stored in settings
    user_flags = settings.get("flags", [])
    if isinstance(user_flags, list):
        flags.extend(user_flags)

    return flags


async def _create_tasks_from_templates(
    db: AsyncSession,
    *,
    matter: Matter,
    templates: list[dict[str, Any]],
    actor_id: uuid.UUID | None,
    existing_key_to_task_id: dict[str, uuid.UUID] | None = None,
) -> list[Task]:
    """Create Task, TaskDependency, and Deadline records from a list of templates.

    Args:
        matter: The matter to create tasks for.
        templates: List of template dicts to materialize.
        actor_id: User/system ID for event logging.
        existing_key_to_task_id: Map of already-existing template_key → task_id
            (used during regeneration to resolve cross-dependencies).

    Returns:
        List of newly created Task objects.
    """
    matter_created = matter.created_at.date() if matter.created_at else date.today()

    # Phase counters for sort_order assignment
    phase_counters: dict[str, int] = {}

    # First pass: create all Task rows (need IDs before creating dependencies)
    new_tasks: list[Task] = []
    template_order: list[dict[str, Any]] = []  # parallel to new_tasks

    for tmpl in templates:
        phase_str = tmpl.get("phase", "custom")
        priority_str = tmpl.get("priority", "normal")

        # Resolve enum values safely
        try:
            phase = TaskPhase(phase_str)
        except ValueError:
            phase = TaskPhase.custom
        try:
            priority = TaskPriority(priority_str)
        except ValueError:
            priority = TaskPriority.normal

        # Calculate sort_order
        base_order = _PHASE_BASE_ORDER.get(phase_str, 8000)
        counter = phase_counters.get(phase_str, 0)
        phase_counters[phase_str] = counter + 1
        sort_order = base_order + (counter + 1) * 10

        # Resolve due date
        due_date_rule = tmpl.get("due_date_rule")
        due_date = _resolve_due_date(due_date_rule, matter.date_of_death, matter_created)

        task = Task(
            matter_id=matter.id,
            template_key=tmpl.get("key"),
            title=tmpl.get("title", ""),
            description=tmpl.get("description"),
            instructions=tmpl.get("instructions"),
            phase=phase,
            priority=priority,
            requires_document=tmpl.get("requires_document", False),
            due_date=due_date,
            due_date_rule=due_date_rule,
            sort_order=sort_order,
            metadata_={"default_assignee_role": tmpl.get("default_assignee_role")},
        )
        db.add(task)
        new_tasks.append(task)
        template_order.append(tmpl)

    # Flush to assign IDs
    if new_tasks:
        await db.flush()

    # Build key → task_id map (merge existing + new)
    key_to_id: dict[str, uuid.UUID] = dict(existing_key_to_task_id or {})
    for task in new_tasks:
        if task.template_key:
            key_to_id[task.template_key] = task.id

    # Second pass: create dependencies
    for task, tmpl in zip(new_tasks, template_order):
        dep_keys = tmpl.get("dependencies") or []
        for dep_key in dep_keys:
            dep_task_id = key_to_id.get(dep_key)
            if dep_task_id is None:
                logger.warning(
                    "Dependency '%s' not found for task '%s' — skipping",
                    dep_key,
                    tmpl.get("key"),
                )
                continue
            dep = TaskDependency(task_id=task.id, depends_on_task_id=dep_task_id)
            db.add(dep)

    # Third pass: create deadlines for tasks with due dates
    for task, tmpl in zip(new_tasks, template_order):
        if task.due_date is not None:
            deadline = Deadline(
                matter_id=matter.id,
                task_id=task.id,
                title=task.title,
                description=task.description,
                due_date=task.due_date,
                source=DeadlineSource.auto,
                rule=tmpl.get("due_date_rule"),
            )
            db.add(deadline)

    if new_tasks:
        await db.flush()

    # Event-log each created task
    for task in new_tasks:
        await event_logger.log(
            db,
            matter_id=matter.id,
            actor_id=actor_id,
            actor_type=ActorType.system,
            entity_type="task",
            entity_id=task.id,
            action="generated",
            metadata={
                "template_key": task.template_key,
                "title": task.title,
                "phase": task.phase.value,
            },
        )

    return new_tasks


async def _create_state_deadlines(
    db: AsyncSession,
    *,
    matter: Matter,
    actor_id: uuid.UUID | None,
    existing_deadline_keys: set[str] | None = None,
) -> int:
    """Create standalone state-specific deadlines (not linked to a task).

    Returns count of created deadlines.
    """
    state = matter.jurisdiction_state.upper() if matter.jurisdiction_state else ""
    estate_type = (
        matter.estate_type.value
        if hasattr(matter.estate_type, "value")
        else str(matter.estate_type)
    )
    state_deadlines = template_registry.get_state_deadlines(state, estate_type)

    if not state_deadlines:
        return 0

    matter_created = matter.created_at.date() if matter.created_at else date.today()
    skip_keys = existing_deadline_keys or set()
    count = 0

    for dl in state_deadlines:
        dl_key = dl.get("key", "")
        if dl_key in skip_keys:
            continue

        due_date = _resolve_due_date(
            {
                "relative_to": dl.get("relative_to", "matter_created"),
                "offset_days": dl.get("offset_days"),
                "offset_months": dl.get("offset_months"),
            },
            matter.date_of_death,
            matter_created,
        )
        if due_date is None:
            continue

        deadline = Deadline(
            matter_id=matter.id,
            title=dl.get("title", ""),
            description=dl.get("description"),
            due_date=due_date,
            source=DeadlineSource.auto,
            rule={
                "key": dl_key,
                "relative_to": dl.get("relative_to"),
                "offset_days": dl.get("offset_days"),
                "offset_months": dl.get("offset_months"),
            },
        )
        db.add(deadline)
        count += 1

        await event_logger.log(
            db,
            matter_id=matter.id,
            actor_id=actor_id,
            actor_type=ActorType.system,
            entity_type="deadline",
            entity_id=matter.id,  # placeholder; flushed ID not yet available
            action="generated",
            metadata={"key": dl_key, "title": dl.get("title")},
        )

    if count:
        await db.flush()

    return count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_tasks(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    actor_id: uuid.UUID | None = None,
) -> list[Task]:
    """Generate tasks from templates for a matter.

    Called on matter creation. Creates Task, TaskDependency, and Deadline records.
    """
    matter = await _fetch_matter(db, matter_id)
    estate_type = (
        matter.estate_type.value
        if hasattr(matter.estate_type, "value")
        else str(matter.estate_type)
    )
    state = matter.jurisdiction_state.upper() if matter.jurisdiction_state else ""
    flags = _get_matter_flags(matter)

    templates = template_registry.get_templates(estate_type, state, flags)
    logger.info(
        "Generating %d tasks for matter %s (type=%s, state=%s)",
        len(templates),
        matter_id,
        estate_type,
        state,
    )

    new_tasks = await _create_tasks_from_templates(
        db, matter=matter, templates=templates, actor_id=actor_id
    )

    # Create standalone state deadlines
    deadline_count = await _create_state_deadlines(db, matter=matter, actor_id=actor_id)

    logger.info(
        "Generated %d tasks and %d state deadlines for matter %s",
        len(new_tasks),
        deadline_count,
        matter_id,
    )

    return new_tasks


async def regenerate_tasks(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    actor_id: uuid.UUID | None = None,
) -> list[Task]:
    """Add missing template tasks without duplicating existing ones.

    Compares current templates against existing tasks (by template_key).
    Only creates tasks for templates not yet present.
    """
    matter = await _fetch_matter(db, matter_id)
    estate_type = (
        matter.estate_type.value
        if hasattr(matter.estate_type, "value")
        else str(matter.estate_type)
    )
    state = matter.jurisdiction_state.upper() if matter.jurisdiction_state else ""
    flags = _get_matter_flags(matter)

    templates = template_registry.get_templates(estate_type, state, flags)

    # Find existing template keys for this matter
    existing_q = select(Task.template_key, Task.id).where(
        Task.matter_id == matter_id, Task.template_key.isnot(None)
    )
    result = await db.execute(existing_q)
    existing_key_to_id: dict[str, uuid.UUID] = {}
    for row in result.all():
        if row.template_key:
            existing_key_to_id[row.template_key] = row.id

    existing_keys = set(existing_key_to_id.keys())

    # Filter to only new templates
    new_templates = [t for t in templates if t.get("key") not in existing_keys]

    if not new_templates:
        logger.info("No new tasks to generate for matter %s", matter_id)
        return []

    logger.info(
        "Regenerating: %d new tasks for matter %s (skipping %d existing)",
        len(new_templates),
        matter_id,
        len(existing_keys),
    )

    new_tasks = await _create_tasks_from_templates(
        db,
        matter=matter,
        templates=new_templates,
        actor_id=actor_id,
        existing_key_to_task_id=existing_key_to_id,
    )

    # Regenerate missing state deadlines
    existing_deadline_q = select(Deadline.rule).where(
        Deadline.matter_id == matter_id,
        Deadline.source == DeadlineSource.auto,
        Deadline.task_id.is_(None),
    )
    dl_result = await db.execute(existing_deadline_q)
    existing_dl_keys: set[str] = set()
    for row in dl_result.all():
        if row.rule and isinstance(row.rule, dict):
            k = row.rule.get("key")
            if k:
                existing_dl_keys.add(k)

    await _create_state_deadlines(
        db, matter=matter, actor_id=actor_id, existing_deadline_keys=existing_dl_keys
    )

    return new_tasks
