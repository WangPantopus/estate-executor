"""Task management API routes."""

from __future__ import annotations

import contextlib
import math
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.security import get_current_user, require_firm_member, require_stakeholder
from app.models.enums import StakeholderRole, TaskPhase, TaskPriority, TaskStatus
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.models.tasks import Task as TaskModel
from app.schemas.auth import CurrentUser
from app.schemas.common import PaginationMeta, PaginationParams
from app.schemas.tasks import (
    CommentBrief,
    DocumentBrief,
    TaskAssign,
    TaskComplete,
    TaskCreate,
    TaskDetailResponse,
    TaskGenerateRequest,
    TaskLinkDocument,
    TaskListItem,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
    TaskWaive,
)
from app.services import task_generation_service, task_service

router = APIRouter()

# Roles allowed to create/update any task
_WRITE_ROLES = {StakeholderRole.matter_admin, StakeholderRole.professional}


# ---------------------------------------------------------------------------
# GET /firms/{firm_id}/matters/{matter_id}/tasks — List tasks
# ---------------------------------------------------------------------------


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    firm_id: UUID,
    matter_id: UUID,
    phase: TaskPhase | None = Query(None),
    status: TaskStatus | None = Query(None),
    priority: TaskPriority | None = Query(None),
    assigned_to: UUID | None = Query(None),
    search: str | None = Query(None, description="Search task title"),
    sort_by: str = Query("sort_order", pattern="^(sort_order|due_date|created_at)$"),
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TaskListResponse:
    """List tasks with filters, sorting, and pagination.

    Role-based filtering:
    - beneficiary: only milestone/informational tasks
    - read_only: only milestone/informational tasks
    - executor_trustee: only tasks assigned to them
    - matter_admin/professional: all tasks
    """
    # Beneficiary and read_only only see milestones
    if stakeholder.role in (StakeholderRole.beneficiary, StakeholderRole.read_only):
        phase = TaskPhase.family_communication if phase is None else phase
    # Executor/trustee only see their assigned tasks
    effective_assigned_to = assigned_to
    if stakeholder.role == StakeholderRole.executor_trustee and stakeholder.id is not None:
        effective_assigned_to = stakeholder.id

    items, total = await task_service.list_tasks(
        db,
        matter_id=matter_id,
        phase=phase,
        status=status,
        priority=priority,
        assigned_to=effective_assigned_to,
        search=search,
        sort_by=sort_by,
        page=pagination.page,
        per_page=pagination.per_page,
    )
    return TaskListResponse(
        data=[TaskListItem(**item) for item in items],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0,
        ),
    )


# ---------------------------------------------------------------------------
# POST /firms/{firm_id}/matters/{matter_id}/tasks — Create custom task
# ---------------------------------------------------------------------------


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    firm_id: UUID,
    matter_id: UUID,
    body: TaskCreate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Create a custom task. Requires matter_admin or professional role."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Only matter admins and professionals can create tasks")

    task = await task_service.create_task(
        db,
        matter_id=matter_id,
        title=body.title,
        phase=body.phase,
        description=body.description,
        instructions=body.instructions,
        priority=body.priority,
        assigned_to=body.assigned_to,
        due_date=body.due_date,
        requires_document=body.requires_document,
        parent_task_id=body.parent_task_id,
        dependency_ids=body.dependency_ids,
        current_user=current_user,
    )
    # Build response — freshly created task has no documents/dependencies loaded
    dep_ids = body.dependency_ids or []
    return TaskResponse(
        id=task.id,
        matter_id=task.matter_id,
        parent_task_id=task.parent_task_id,
        template_key=task.template_key,
        title=task.title,
        description=task.description,
        instructions=task.instructions,
        phase=task.phase,
        status=task.status,
        priority=task.priority,
        assigned_to=task.assigned_to,
        due_date=task.due_date,
        requires_document=task.requires_document,
        completed_at=task.completed_at,
        completed_by=task.completed_by,
        sort_order=task.sort_order,
        metadata=task.metadata_,
        documents=[],
        dependencies=dep_ids,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


# ---------------------------------------------------------------------------
# POST /firms/{firm_id}/matters/{matter_id}/tasks/generate — (Re)generate tasks
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=TaskListResponse)
async def generate_tasks_endpoint(
    firm_id: UUID,
    matter_id: UUID,
    body: TaskGenerateRequest | None = None,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskListResponse:
    """Trigger task (re)generation from templates.

    With regenerate=true, only adds missing tasks without modifying existing ones.
    """
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(
            detail="Only matter admins and professionals can generate tasks"
        )

    if body and body.regenerate:
        tasks = await task_generation_service.regenerate_tasks(
            db, matter_id=matter_id, actor_id=current_user.user_id
        )
    else:
        tasks = await task_generation_service.generate_tasks(
            db, matter_id=matter_id, actor_id=current_user.user_id
        )

    items = [
        TaskListItem(
            id=t.id,
            matter_id=t.matter_id,
            parent_task_id=t.parent_task_id,
            template_key=t.template_key,
            title=t.title,
            description=t.description,
            instructions=t.instructions,
            phase=t.phase,
            status=t.status,
            priority=t.priority,
            assigned_to=t.assigned_to,
            due_date=t.due_date,
            requires_document=t.requires_document,
            completed_at=t.completed_at,
            completed_by=t.completed_by,
            sort_order=t.sort_order,
            metadata=t.metadata_,
            document_count=0,
            dependency_ids=[],
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tasks
    ]

    return TaskListResponse(
        data=items,
        meta=PaginationMeta(
            total=len(items),
            page=1,
            per_page=len(items) or 50,
            total_pages=1 if items else 0,
        ),
    )


# ---------------------------------------------------------------------------
# GET /firms/{firm_id}/matters/{matter_id}/tasks/{task_id} — Task detail
# ---------------------------------------------------------------------------


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task_detail(
    firm_id: UUID,
    matter_id: UUID,
    task_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> TaskDetailResponse:
    """Get full task detail with documents, dependencies, dependents, and comments.

    Beneficiaries and read_only users cannot access task detail.
    Executor/trustees can only access tasks assigned to them.
    """
    from app.core.exceptions import NotFoundError

    if stakeholder.role in (StakeholderRole.beneficiary, StakeholderRole.read_only):
        raise NotFoundError(detail="Task not found")

    detail = await task_service.get_task_detail(db, task_id=task_id, matter_id=matter_id)

    # Executor/trustee can only see assigned tasks
    if (
        stakeholder.role == StakeholderRole.executor_trustee
        and stakeholder.id is not None
        and detail.get("assigned_to") != stakeholder.id
    ):
        raise NotFoundError(detail="Task not found")
    return TaskDetailResponse(
        id=detail["id"],
        matter_id=detail["matter_id"],
        parent_task_id=detail["parent_task_id"],
        template_key=detail["template_key"],
        title=detail["title"],
        description=detail["description"],
        instructions=detail["instructions"],
        phase=detail["phase"],
        status=detail["status"],
        priority=detail["priority"],
        assigned_to=detail["assigned_to"],
        due_date=detail["due_date"],
        requires_document=detail["requires_document"],
        completed_at=detail["completed_at"],
        completed_by=detail["completed_by"],
        sort_order=detail["sort_order"],
        metadata=detail["metadata"],
        documents=[DocumentBrief(**d) for d in detail["documents"]],
        dependencies=detail["dependencies"],
        dependents=detail["dependents"],
        comments=[CommentBrief(**c) for c in detail["comments"]],
        created_at=detail["created_at"],
        updated_at=detail["updated_at"],
    )


# ---------------------------------------------------------------------------
# PATCH /firms/{firm_id}/matters/{matter_id}/tasks/{task_id} — Update task
# ---------------------------------------------------------------------------


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    firm_id: UUID,
    matter_id: UUID,
    task_id: UUID,
    body: TaskUpdate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Update a task. Permission depends on role and assignment."""
    _check_task_write_permission(stakeholder, task_id)

    updates = body.model_dump(exclude_unset=True)
    task = await task_service.update_task(
        db,
        task_id=task_id,
        matter_id=matter_id,
        updates=updates,
        current_user=current_user,
    )
    return _task_to_response(task)


# ---------------------------------------------------------------------------
# POST .../tasks/{task_id}/complete — Mark complete
# ---------------------------------------------------------------------------


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    firm_id: UUID,
    matter_id: UUID,
    task_id: UUID,
    body: TaskComplete | None = None,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Mark a task as complete. Validates document requirements and dependencies."""
    _check_task_complete_permission(stakeholder, task_id)

    task, _unblocked = await task_service.complete_task(
        db,
        task_id=task_id,
        matter_id=matter_id,
        stakeholder=stakeholder,
        current_user=current_user,
        notes=body.notes if body else None,
    )
    return _task_to_response(task)


# ---------------------------------------------------------------------------
# POST .../tasks/{task_id}/waive — Waive task
# ---------------------------------------------------------------------------


@router.post("/{task_id}/waive", response_model=TaskResponse)
async def waive_task(
    firm_id: UUID,
    matter_id: UUID,
    task_id: UUID,
    body: TaskWaive,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Waive a task with a required reason."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Only matter admins and professionals can waive tasks")

    task, _unblocked = await task_service.waive_task(
        db,
        task_id=task_id,
        matter_id=matter_id,
        reason=body.reason,
        current_user=current_user,
    )
    return _task_to_response(task)


# ---------------------------------------------------------------------------
# POST .../tasks/{task_id}/assign — Assign task
# ---------------------------------------------------------------------------


@router.post("/{task_id}/assign", response_model=TaskResponse)
async def assign_task(
    firm_id: UUID,
    matter_id: UUID,
    task_id: UUID,
    body: TaskAssign,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Assign a task to a stakeholder. Requires matter_admin or professional role."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Only matter admins and professionals can assign tasks")

    task = await task_service.assign_task(
        db,
        task_id=task_id,
        matter_id=matter_id,
        stakeholder_id=body.stakeholder_id,
        current_user=current_user,
    )
    return _task_to_response(task)


# ---------------------------------------------------------------------------
# POST .../tasks/{task_id}/documents — Link document to task
# ---------------------------------------------------------------------------


@router.post("/{task_id}/documents", status_code=201)
async def link_document(
    firm_id: UUID,
    matter_id: UUID,
    task_id: UUID,
    body: TaskLinkDocument,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Link a document to a task. Requires at least executor_trustee role."""
    if stakeholder.role in (StakeholderRole.beneficiary, StakeholderRole.read_only):
        raise PermissionDeniedError(detail="Insufficient permissions")
    await task_service.link_document(
        db,
        task_id=task_id,
        matter_id=matter_id,
        document_id=body.document_id,
        current_user=current_user,
    )
    return {"status": "linked"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_task_write_permission(stakeholder: Stakeholder, task_id: UUID) -> None:
    """Check write permission: admins/professionals can update any task,
    executor_trustees can only update tasks assigned to them."""
    if stakeholder.role in _WRITE_ROLES:
        return
    if stakeholder.role == StakeholderRole.executor_trustee and stakeholder.id is not None:
        # Executor/trustees are allowed — actual assignment check happens in service
        return
    raise PermissionDeniedError(detail="Insufficient permissions to update this task")


def _check_task_complete_permission(stakeholder: Stakeholder, task_id: UUID) -> None:
    """Check complete permission: admins/professionals can complete any task,
    executor_trustees can complete tasks assigned to them."""
    if stakeholder.role in _WRITE_ROLES:
        return
    if stakeholder.role == StakeholderRole.executor_trustee and stakeholder.id is not None:
        return
    raise PermissionDeniedError(detail="Insufficient permissions to complete this task")


def _task_to_response(task: object) -> TaskResponse:
    """Convert a Task ORM model to TaskResponse.

    Handles the case where relationships may not be loaded.
    """

    t: TaskModel = task  # type: ignore[assignment]
    docs = []
    deps: list[UUID] = []
    with contextlib.suppress(Exception):
        docs = [
            DocumentBrief(
                id=d.id, filename=d.filename, doc_type=d.doc_type, created_at=d.created_at
            )
            for d in t.documents
        ]
    with contextlib.suppress(Exception):
        deps = [dep.depends_on_task_id for dep in t.dependencies]

    return TaskResponse(
        id=t.id,
        matter_id=t.matter_id,
        parent_task_id=t.parent_task_id,
        template_key=t.template_key,
        title=t.title,
        description=t.description,
        instructions=t.instructions,
        phase=t.phase,
        status=t.status,
        priority=t.priority,
        assigned_to=t.assigned_to,
        due_date=t.due_date,
        requires_document=t.requires_document,
        completed_at=t.completed_at,
        completed_by=t.completed_by,
        sort_order=t.sort_order,
        metadata=t.metadata_,
        documents=docs,
        dependencies=deps,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )
