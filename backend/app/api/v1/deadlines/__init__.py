"""Deadline management API routes."""

from __future__ import annotations

import math
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.security import get_current_user, require_firm_member, require_stakeholder
from app.models.deadlines import Deadline
from app.models.enums import DeadlineStatus, StakeholderRole
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.schemas.auth import CurrentUser
from app.schemas.common import PaginationMeta, PaginationParams
from app.schemas.deadlines import (
    CalendarDeadline,
    CalendarMonth,
    CalendarResponse,
    DeadlineCreate,
    DeadlineListResponse,
    DeadlineResponse,
    DeadlineUpdate,
    TaskBrief,
)
from app.services import deadline_service

router = APIRouter()

_WRITE_ROLES = {StakeholderRole.matter_admin, StakeholderRole.professional}


def _deadline_to_response(dl: Deadline) -> DeadlineResponse:
    """Convert a Deadline ORM object to DeadlineResponse."""
    task_brief = None
    if dl.task is not None:
        task_brief = TaskBrief(
            id=dl.task.id,
            title=dl.task.title,
            status=dl.task.status.value,
        )
    return DeadlineResponse(
        id=dl.id,
        matter_id=dl.matter_id,
        task_id=dl.task_id,
        title=dl.title,
        description=dl.description,
        due_date=dl.due_date,
        source=dl.source,
        rule=dl.rule,
        status=dl.status,
        assigned_to=dl.assigned_to,
        assignee_name=dl.assignee.full_name if dl.assignee else None,
        task=task_brief,
        reminder_config=dl.reminder_config,
        last_reminder_sent=dl.last_reminder_sent,
        created_at=dl.created_at,
        updated_at=dl.updated_at,
    )


# ---------------------------------------------------------------------------
# POST /firms/{firm_id}/matters/{matter_id}/deadlines — Create manual deadline
# ---------------------------------------------------------------------------


@router.post("", response_model=DeadlineResponse, status_code=201)
async def create_deadline(
    firm_id: UUID,
    matter_id: UUID,
    body: DeadlineCreate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeadlineResponse:
    """Create a manual deadline."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(
            detail="Only matter admins and professionals can create deadlines"
        )

    deadline = await deadline_service.create_deadline(
        db,
        matter_id=matter_id,
        title=body.title,
        description=body.description,
        due_date=body.due_date,
        task_id=body.task_id,
        assigned_to=body.assigned_to,
        reminder_config=body.reminder_config,
        current_user=current_user,
    )
    return _deadline_to_response(deadline)


# ---------------------------------------------------------------------------
# GET /firms/{firm_id}/matters/{matter_id}/deadlines — List deadlines
# ---------------------------------------------------------------------------


@router.get("", response_model=DeadlineListResponse)
async def list_deadlines(
    firm_id: UUID,
    matter_id: UUID,
    status: DeadlineStatus | None = Query(None),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> DeadlineListResponse:
    """List deadlines with optional filters, sorted by due_date ascending."""
    deadlines, total = await deadline_service.list_deadlines(
        db,
        matter_id=matter_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=pagination.page,
        per_page=pagination.per_page,
    )
    return DeadlineListResponse(
        data=[_deadline_to_response(dl) for dl in deadlines],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0,
        ),
    )


# ---------------------------------------------------------------------------
# PATCH /firms/{firm_id}/matters/{matter_id}/deadlines/{deadline_id} — Update
# ---------------------------------------------------------------------------


@router.patch("/{deadline_id}", response_model=DeadlineResponse)
async def update_deadline(
    firm_id: UUID,
    matter_id: UUID,
    deadline_id: UUID,
    body: DeadlineUpdate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeadlineResponse:
    """Update a deadline. Tracks due_date changes with original/new dates."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(
            detail="Only matter admins and professionals can update deadlines"
        )

    updates = body.model_dump(exclude_unset=True)
    deadline = await deadline_service.update_deadline(
        db,
        deadline_id=deadline_id,
        matter_id=matter_id,
        updates=updates,
        current_user=current_user,
    )
    return _deadline_to_response(deadline)


# ---------------------------------------------------------------------------
# GET .../deadlines/calendar — Calendar view grouped by month
# ---------------------------------------------------------------------------


@router.get("/calendar", response_model=CalendarResponse)
async def get_calendar(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> CalendarResponse:
    """Return deadlines grouped by month for the calendar widget."""
    months = await deadline_service.get_calendar(db, matter_id=matter_id)
    return CalendarResponse(
        data=[
            CalendarMonth(
                month=m["month"],
                deadlines=[CalendarDeadline(**d) for d in m["deadlines"]],
            )
            for m in months
        ]
    )
