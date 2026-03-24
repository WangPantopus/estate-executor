"""Task business logic service layer — CRUD, state machine, and cascading actions."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.events import event_logger
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.documents import Document
from app.models.enums import ActorType, TaskPhase, TaskPriority, TaskStatus
from app.models.stakeholders import Stakeholder
from app.models.task_dependencies import TaskDependency
from app.models.task_documents import task_documents
from app.models.tasks import Task

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[TaskStatus, list[TaskStatus]] = {
    TaskStatus.not_started: [
        TaskStatus.in_progress,
        TaskStatus.blocked,
        TaskStatus.waived,
        TaskStatus.cancelled,
    ],
    TaskStatus.in_progress: [
        TaskStatus.complete,
        TaskStatus.blocked,
        TaskStatus.waived,
        TaskStatus.cancelled,
    ],
    TaskStatus.blocked: [
        TaskStatus.not_started,
        TaskStatus.in_progress,
        TaskStatus.waived,
        TaskStatus.cancelled,
    ],
    TaskStatus.complete: [],
    TaskStatus.waived: [],
    TaskStatus.cancelled: [],
}

TERMINAL_STATES = {TaskStatus.complete, TaskStatus.waived, TaskStatus.cancelled}


def _validate_transition(current: TaskStatus, target: TaskStatus) -> None:
    """Raise ConflictError if the transition is not allowed."""
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        if current in TERMINAL_STATES:
            raise ConflictError(
                detail=f"Task is in terminal state '{current.value}' and cannot be changed"
            )
        raise ConflictError(
            detail=(
                f"Invalid state transition from '{current.value}' to '{target.value}'. "
                f"Allowed transitions: {[s.value for s in allowed]}"
            )
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_task_or_404(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    matter_id: uuid.UUID,
) -> Task:
    """Fetch a task by ID scoped to a matter, or raise 404."""
    result = await db.execute(select(Task).where(Task.id == task_id, Task.matter_id == matter_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise NotFoundError(detail="Task not found")
    return task


async def _unblock_dependents(db: AsyncSession, *, task: Task) -> list[uuid.UUID]:
    """Check dependents of a newly-completed/waived task and unblock them if ready.

    A dependent is unblocked (blocked → not_started) when ALL of its dependencies
    are in a terminal state.

    Returns list of unblocked task IDs.
    """
    # Find tasks that depend on this task
    dependent_q = select(TaskDependency.task_id).where(TaskDependency.depends_on_task_id == task.id)
    dependent_ids = [row[0] for row in (await db.execute(dependent_q)).all()]

    if not dependent_ids:
        return []

    unblocked: list[uuid.UUID] = []

    for dep_task_id in dependent_ids:
        # Fetch the dependent task
        result = await db.execute(select(Task).where(Task.id == dep_task_id))
        dep_task = result.scalar_one_or_none()
        if dep_task is None or dep_task.status != TaskStatus.blocked:
            continue

        # Check if ALL dependencies of this dependent are now terminal
        all_deps_q = select(TaskDependency.depends_on_task_id).where(
            TaskDependency.task_id == dep_task_id
        )
        all_dep_ids = [row[0] for row in (await db.execute(all_deps_q)).all()]

        if not all_dep_ids:
            continue

        non_terminal_q = (
            select(func.count())
            .select_from(Task)
            .where(
                Task.id.in_(all_dep_ids),
                Task.status.notin_(list(TERMINAL_STATES)),
            )
        )
        non_terminal_count = (await db.execute(non_terminal_q)).scalar_one()

        if non_terminal_count == 0:
            dep_task.status = TaskStatus.not_started
            await db.flush()
            unblocked.append(dep_task_id)

            await event_logger.log(
                db,
                matter_id=dep_task.matter_id,
                actor_id=None,
                actor_type=ActorType.system,
                entity_type="task",
                entity_id=dep_task_id,
                action="unblocked",
                changes={"status": {"old": "blocked", "new": "not_started"}},
                metadata={"unblocked_by": str(task.id)},
            )

    return unblocked


# ---------------------------------------------------------------------------
# List tasks
# ---------------------------------------------------------------------------


async def list_tasks(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    phase: TaskPhase | None = None,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assigned_to: uuid.UUID | None = None,
    search: str | None = None,
    sort_by: str = "sort_order",
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """List tasks with filters, sorting, document count, and dependency IDs.

    Returns a list of dicts ready for TaskListItem serialization.
    """
    base_filters = [Task.matter_id == matter_id]

    if phase is not None:
        base_filters.append(Task.phase == phase)
    if status is not None:
        base_filters.append(Task.status == status)
    if priority is not None:
        base_filters.append(Task.priority == priority)
    if assigned_to is not None:
        base_filters.append(Task.assigned_to == assigned_to)
    if search:
        base_filters.append(Task.title.ilike(f"%{search}%"))

    # Count
    count_q = select(func.count()).select_from(Task).where(*base_filters)
    total = (await db.execute(count_q)).scalar_one()

    # Sort
    sort_column = {
        "sort_order": Task.sort_order,
        "due_date": Task.due_date,
        "created_at": Task.created_at,
    }.get(sort_by, Task.sort_order)

    # Fetch tasks
    q = (
        select(Task)
        .options(selectinload(Task.dependencies))
        .where(*base_filters)
        .order_by(sort_column, Task.created_at)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    tasks = list(result.scalars().all())

    if not tasks:
        return [], total

    task_ids = [t.id for t in tasks]

    # Document counts per task (single query)
    doc_count_q = (
        select(
            task_documents.c.task_id,
            func.count().label("cnt"),
        )
        .where(task_documents.c.task_id.in_(task_ids))
        .group_by(task_documents.c.task_id)
    )
    doc_counts = {row.task_id: row.cnt for row in (await db.execute(doc_count_q)).all()}

    items: list[dict[str, Any]] = []
    for task in tasks:
        items.append(
            {
                "id": task.id,
                "matter_id": task.matter_id,
                "parent_task_id": task.parent_task_id,
                "template_key": task.template_key,
                "title": task.title,
                "description": task.description,
                "instructions": task.instructions,
                "phase": task.phase,
                "status": task.status,
                "priority": task.priority,
                "assigned_to": task.assigned_to,
                "due_date": task.due_date,
                "requires_document": task.requires_document,
                "completed_at": task.completed_at,
                "completed_by": task.completed_by,
                "sort_order": task.sort_order,
                "metadata": task.metadata_,
                "document_count": doc_counts.get(task.id, 0),
                "dependency_ids": [dep.depends_on_task_id for dep in task.dependencies],
                "created_at": task.created_at,
                "updated_at": task.updated_at,
            }
        )

    return items, total


# ---------------------------------------------------------------------------
# Get task detail
# ---------------------------------------------------------------------------


async def get_task_detail(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    matter_id: uuid.UUID,
) -> dict[str, Any]:
    """Get full task detail including documents, dependencies, dependents, and comments."""
    result = await db.execute(
        select(Task)
        .options(
            selectinload(Task.documents),
            selectinload(Task.dependencies),
            selectinload(Task.dependents),
            selectinload(Task.comments),
        )
        .where(Task.id == task_id, Task.matter_id == matter_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise NotFoundError(detail="Task not found")

    return {
        "id": task.id,
        "matter_id": task.matter_id,
        "parent_task_id": task.parent_task_id,
        "template_key": task.template_key,
        "title": task.title,
        "description": task.description,
        "instructions": task.instructions,
        "phase": task.phase,
        "status": task.status,
        "priority": task.priority,
        "assigned_to": task.assigned_to,
        "due_date": task.due_date,
        "requires_document": task.requires_document,
        "completed_at": task.completed_at,
        "completed_by": task.completed_by,
        "sort_order": task.sort_order,
        "metadata": task.metadata_,
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "doc_type": doc.doc_type,
                "created_at": doc.created_at,
            }
            for doc in task.documents
        ],
        "dependencies": [dep.depends_on_task_id for dep in task.dependencies],
        "dependents": [dep.task_id for dep in task.dependents],
        "comments": [
            {
                "id": c.id,
                "author_id": c.author_id,
                "body": c.body,
                "created_at": c.created_at,
            }
            for c in task.comments
        ],
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


# ---------------------------------------------------------------------------
# Create task
# ---------------------------------------------------------------------------


async def create_task(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    title: str,
    phase: TaskPhase,
    description: str | None = None,
    instructions: str | None = None,
    priority: TaskPriority | None = None,
    assigned_to: uuid.UUID | None = None,
    due_date: Any = None,
    requires_document: bool | None = None,
    parent_task_id: uuid.UUID | None = None,
    dependency_ids: list[uuid.UUID] | None = None,
    current_user: CurrentUser,
) -> Task:
    """Create a custom task. Validates dependencies belong to this matter."""
    # Validate parent task if provided
    if parent_task_id is not None:
        await _get_task_or_404(db, task_id=parent_task_id, matter_id=matter_id)

    # Validate assigned_to stakeholder
    if assigned_to is not None:
        result = await db.execute(
            select(Stakeholder).where(
                Stakeholder.id == assigned_to,
                Stakeholder.matter_id == matter_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise BadRequestError(detail="Assigned stakeholder not found on this matter")

    # Validate dependency IDs
    if dependency_ids:
        dep_count_q = (
            select(func.count())
            .select_from(Task)
            .where(Task.id.in_(dependency_ids), Task.matter_id == matter_id)
        )
        found = (await db.execute(dep_count_q)).scalar_one()
        if found != len(dependency_ids):
            raise BadRequestError(detail="One or more dependency tasks not found on this matter")

    task = Task(
        matter_id=matter_id,
        title=title,
        phase=phase,
        description=description,
        instructions=instructions,
        priority=priority or TaskPriority.normal,
        assigned_to=assigned_to,
        due_date=due_date,
        requires_document=requires_document or False,
        parent_task_id=parent_task_id,
    )
    db.add(task)
    await db.flush()

    # Create dependency records
    if dependency_ids:
        for dep_id in dependency_ids:
            dep = TaskDependency(task_id=task.id, depends_on_task_id=dep_id)
            db.add(dep)
        await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="task",
        entity_id=task.id,
        action="created",
        metadata={
            "title": title,
            "phase": phase.value,
            "dependency_count": len(dependency_ids) if dependency_ids else 0,
        },
    )

    return task


# ---------------------------------------------------------------------------
# Update task
# ---------------------------------------------------------------------------


async def update_task(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    matter_id: uuid.UUID,
    updates: dict[str, Any],
    current_user: CurrentUser,
) -> Task:
    """Update a task. Status changes are validated against the state machine."""
    task = await _get_task_or_404(db, task_id=task_id, matter_id=matter_id)

    # If status change is requested, validate the transition
    new_status = updates.get("status")
    if new_status is not None:
        _validate_transition(task.status, new_status)

    changes: dict[str, Any] = {}
    for field, value in updates.items():
        if value is None:
            continue
        # Map 'metadata' to 'metadata_' on the model
        attr_name = "metadata_" if field == "metadata" else field
        old_value = getattr(task, attr_name, None)
        old_cmp = old_value.value if hasattr(old_value, "value") else old_value  # type: ignore[union-attr]
        new_cmp = value.value if hasattr(value, "value") else value
        if old_cmp != new_cmp:
            old_str = str(old_cmp) if old_cmp is not None else None
            new_str = str(new_cmp)
            changes[field] = {"old": old_str, "new": new_str}
            setattr(task, attr_name, value)

    if changes:
        await db.flush()
        await event_logger.log(
            db,
            matter_id=matter_id,
            actor_id=current_user.user_id,
            actor_type=ActorType.user,
            entity_type="task",
            entity_id=task.id,
            action="updated",
            changes=changes,
        )

    return task


# ---------------------------------------------------------------------------
# Complete task
# ---------------------------------------------------------------------------


async def complete_task(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    matter_id: uuid.UUID,
    stakeholder: Stakeholder,
    current_user: CurrentUser,
    notes: str | None = None,
) -> tuple[Task, list[uuid.UUID]]:
    """Mark a task as complete. Validates preconditions, unblocks dependents.

    Returns (updated task, list of unblocked task IDs).
    """
    task = await _get_task_or_404(db, task_id=task_id, matter_id=matter_id)
    old_status = task.status.value

    # Validate state transition
    _validate_transition(task.status, TaskStatus.complete)

    # Validate document requirement
    if task.requires_document:
        doc_count_q = (
            select(func.count())
            .select_from(task_documents)
            .where(task_documents.c.task_id == task_id)
        )
        doc_count = (await db.execute(doc_count_q)).scalar_one()
        if doc_count == 0:
            raise BadRequestError(
                detail="Task requires at least one linked document before completion"
            )

    # Validate all dependencies are in terminal state
    dep_q = select(TaskDependency.depends_on_task_id).where(TaskDependency.task_id == task_id)
    dep_ids = [row[0] for row in (await db.execute(dep_q)).all()]

    if dep_ids:
        blocking_q = select(Task.id, Task.title, Task.status).where(
            Task.id.in_(dep_ids),
            Task.status.notin_(list(TERMINAL_STATES)),
        )
        blocking_tasks = (await db.execute(blocking_q)).all()
        if blocking_tasks:
            blockers = [
                {"id": str(bt.id), "title": bt.title, "status": bt.status.value}
                for bt in blocking_tasks
            ]
            raise BadRequestError(
                detail=(
                    f"Cannot complete: {len(blockers)} dependency task(s) are not complete. "
                    f"Blocking tasks: {blockers}"
                )
            )

    # Apply completion
    task.status = TaskStatus.complete
    task.completed_at = datetime.now(UTC)
    task.completed_by = stakeholder.id
    if notes:
        meta = dict(task.metadata_) if task.metadata_ else {}
        meta["completion_notes"] = notes
        task.metadata_ = meta
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="task",
        entity_id=task.id,
        action="completed",
        changes={"status": {"old": old_status, "new": "complete"}},
        metadata={"notes": notes} if notes else None,
    )

    # Cascade: unblock dependents
    unblocked = await _unblock_dependents(db, task=task)

    # Detect milestones after task completion
    try:
        from app.services.milestone_service import detect_milestones_after_completion

        milestones_fired = await detect_milestones_after_completion(
            db,
            matter_id=matter_id,
            completed_task_phase=task.phase,
            actor_id=current_user.user_id,
        )
        if milestones_fired:
            logger.info(
                "milestones_triggered",
                extra={
                    "task_id": str(task_id),
                    "matter_id": str(matter_id),
                    "milestones": milestones_fired,
                },
            )
    except Exception:
        logger.warning("milestone_detection_failed", exc_info=True)

    return task, unblocked


# ---------------------------------------------------------------------------
# Waive task
# ---------------------------------------------------------------------------


async def waive_task(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    matter_id: uuid.UUID,
    reason: str,
    current_user: CurrentUser,
) -> tuple[Task, list[uuid.UUID]]:
    """Waive a task with a reason. Stores reason in metadata, unblocks dependents.

    Returns (updated task, list of unblocked task IDs).
    """
    task = await _get_task_or_404(db, task_id=task_id, matter_id=matter_id)

    _validate_transition(task.status, TaskStatus.waived)

    old_status = task.status.value
    task.status = TaskStatus.waived
    meta = dict(task.metadata_) if task.metadata_ else {}
    meta["waive_reason"] = reason
    task.metadata_ = meta
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="task",
        entity_id=task.id,
        action="waived",
        changes={"status": {"old": old_status, "new": "waived"}},
        metadata={"reason": reason},
    )

    # Cascade: unblock dependents
    unblocked = await _unblock_dependents(db, task=task)

    return task, unblocked


# ---------------------------------------------------------------------------
# Assign task
# ---------------------------------------------------------------------------


async def assign_task(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    matter_id: uuid.UUID,
    stakeholder_id: uuid.UUID,
    current_user: CurrentUser,
) -> Task:
    """Assign a task to a stakeholder. Validates stakeholder belongs to the matter."""
    task = await _get_task_or_404(db, task_id=task_id, matter_id=matter_id)

    if task.status in TERMINAL_STATES:
        raise ConflictError(detail=f"Cannot assign a task in terminal state '{task.status.value}'")

    # Validate stakeholder
    result = await db.execute(
        select(Stakeholder).where(
            Stakeholder.id == stakeholder_id,
            Stakeholder.matter_id == matter_id,
        )
    )
    target_stakeholder = result.scalar_one_or_none()
    if target_stakeholder is None:
        raise BadRequestError(detail="Stakeholder not found on this matter")

    old_assigned = task.assigned_to
    task.assigned_to = stakeholder_id
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="task",
        entity_id=task.id,
        action="assigned",
        changes={
            "assigned_to": {
                "old": str(old_assigned) if old_assigned else None,
                "new": str(stakeholder_id),
            }
        },
        metadata={"assignee_email": target_stakeholder.email},
    )

    # Dispatch notification (Celery stub)
    logger.info(
        "task_assignment_notification_stub",
        extra={
            "task_id": str(task_id),
            "task_title": task.title,
            "assignee_email": target_stakeholder.email,
            "assignee_name": target_stakeholder.full_name,
        },
    )

    return task


# ---------------------------------------------------------------------------
# Link document to task
# ---------------------------------------------------------------------------


async def link_document(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    matter_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: CurrentUser,
) -> None:
    """Link a document to a task via the task_documents junction table."""
    # Validate task
    await _get_task_or_404(db, task_id=task_id, matter_id=matter_id)

    # Validate document belongs to the same matter
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.matter_id == matter_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise BadRequestError(detail="Document not found on this matter")

    # Check for existing link
    existing_q = select(task_documents).where(
        task_documents.c.task_id == task_id,
        task_documents.c.document_id == document_id,
    )
    if (await db.execute(existing_q)).first() is not None:
        raise ConflictError(detail="Document is already linked to this task")

    await db.execute(task_documents.insert().values(task_id=task_id, document_id=document_id))
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="task",
        entity_id=task_id,
        action="document_linked",
        metadata={"document_id": str(document_id)},
    )
