"""Time tracking API routes."""

from __future__ import annotations

import math
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.security import get_current_user, require_firm_member, require_stakeholder
from app.models.enums import StakeholderRole
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.schemas.auth import CurrentUser
from app.schemas.common import PaginationMeta, PaginationParams
from app.schemas.time_tracking import (
    TimeEntryCreate,
    TimeEntryListResponse,
    TimeEntryResponse,
    TimeEntryUpdate,
    TimeTrackingSummary,
)
from app.services import time_tracking_service

router = APIRouter()

_TIME_ROLES = {
    StakeholderRole.matter_admin,
    StakeholderRole.professional,
}

_VIEW_ROLES = {
    StakeholderRole.matter_admin,
    StakeholderRole.professional,
    StakeholderRole.executor_trustee,
}


def _require_time_entry(stakeholder: Stakeholder) -> None:
    """Only matter_admin and professional can log time."""
    if stakeholder.role not in _TIME_ROLES:
        raise PermissionDeniedError(detail="Only professionals can log time entries")


def _require_time_view(stakeholder: Stakeholder) -> None:
    """matter_admin, professional, and executor_trustee can view time entries."""
    if stakeholder.role not in _VIEW_ROLES:
        raise PermissionDeniedError(detail="Insufficient permissions to view time entries")


def _entry_to_response(entry: Any) -> TimeEntryResponse:
    return TimeEntryResponse(
        id=entry.id,
        matter_id=entry.matter_id,
        task_id=entry.task_id,
        task_title=entry.task.title if entry.task else None,
        stakeholder_id=entry.stakeholder_id,
        stakeholder_name=entry.stakeholder.full_name if entry.stakeholder else "",
        hours=entry.hours,
        minutes=entry.minutes,
        description=entry.description,
        entry_date=entry.entry_date,
        billable=entry.billable,
        created_at=entry.created_at,
    )


# ---------------------------------------------------------------------------
# POST .../time — Create time entry
# ---------------------------------------------------------------------------


@router.post("", response_model=TimeEntryResponse, status_code=201)
async def create_time_entry(
    firm_id: UUID,
    matter_id: UUID,
    body: TimeEntryCreate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TimeEntryResponse:
    """Log a time entry for the current user."""
    _require_time_entry(stakeholder)
    entry = await time_tracking_service.create_time_entry(
        db,
        matter_id=matter_id,
        stakeholder=stakeholder,
        task_id=body.task_id,
        hours=body.hours,
        minutes=body.minutes,
        description=body.description,
        entry_date=body.entry_date,
        billable=body.billable,
        current_user=current_user,
    )
    return _entry_to_response(entry)


# ---------------------------------------------------------------------------
# GET .../time — List time entries
# ---------------------------------------------------------------------------


@router.get("", response_model=TimeEntryListResponse)
async def list_time_entries(
    firm_id: UUID,
    matter_id: UUID,
    task_id: UUID | None = Query(None),
    stakeholder_id: UUID | None = Query(None),
    billable: bool | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TimeEntryListResponse:
    """List time entries with filters and pagination."""
    _require_time_view(_stakeholder)

    from datetime import date as date_type

    parsed_from = date_type.fromisoformat(date_from) if date_from else None
    parsed_to = date_type.fromisoformat(date_to) if date_to else None

    entries, total = await time_tracking_service.list_time_entries(
        db,
        matter_id=matter_id,
        task_id=task_id,
        stakeholder_id=stakeholder_id,
        billable=billable,
        date_from=parsed_from,
        date_to=parsed_to,
        page=pagination.page,
        per_page=pagination.per_page,
    )
    return TimeEntryListResponse(
        data=[_entry_to_response(e) for e in entries],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0,
        ),
    )


# ---------------------------------------------------------------------------
# GET .../time/summary — Time tracking summary
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=TimeTrackingSummary)
async def get_time_summary(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> TimeTrackingSummary:
    """Get aggregated time tracking summary for a matter."""
    _require_time_view(_stakeholder)
    summary = await time_tracking_service.get_time_summary(db, matter_id=matter_id)
    return TimeTrackingSummary(**summary)


# ---------------------------------------------------------------------------
# GET .../time/export — CSV export
# ---------------------------------------------------------------------------


@router.get("/export")
async def export_time_entries(
    firm_id: UUID,
    matter_id: UUID,
    format: str = Query("csv", description="Export format: csv"),  # noqa: A002
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export time entries as CSV for billing system import."""
    _require_time_view(_stakeholder)

    import csv
    import io

    entries, _total = await time_tracking_service.list_time_entries(
        db, matter_id=matter_id, per_page=10000
    )

    # Fetch matter title for the export
    from sqlalchemy import select

    from app.models.matters import Matter

    matter_result = await db.execute(select(Matter.title).where(Matter.id == matter_id))
    matter_title = matter_result.scalar_one_or_none() or "Unknown"

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date",
        "Professional",
        "Task",
        "Hours",
        "Minutes",
        "Decimal Hours",
        "Description",
        "Billable",
        "Matter",
    ])

    for entry in entries:
        total_mins = entry.hours * 60 + entry.minutes
        decimal_hours = round(total_mins / 60, 2)
        writer.writerow([
            entry.entry_date.isoformat(),
            entry.stakeholder.full_name if entry.stakeholder else "",
            entry.task.title if entry.task else "",
            entry.hours,
            entry.minutes,
            decimal_hours,
            entry.description,
            "Yes" if entry.billable else "No",
            matter_title,
        ])

    csv_bytes = output.getvalue().encode("utf-8-sig")  # BOM for Excel compatibility
    filename = f"time-tracking-{matter_title.replace(' ', '_')}.csv"

    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(csv_bytes)),
        },
    )


# ---------------------------------------------------------------------------
# PUT .../time/{entry_id} — Update time entry
# ---------------------------------------------------------------------------


@router.put("/{entry_id}", response_model=TimeEntryResponse)
async def update_time_entry(
    firm_id: UUID,
    matter_id: UUID,
    entry_id: UUID,
    body: TimeEntryUpdate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TimeEntryResponse:
    """Update a time entry. Only the author can edit their own entries."""
    _require_time_entry(stakeholder)
    entry = await time_tracking_service.update_time_entry(
        db,
        entry_id=entry_id,
        matter_id=matter_id,
        stakeholder=stakeholder,
        current_user=current_user,
        task_id=body.task_id,
        hours=body.hours,
        minutes=body.minutes,
        description=body.description,
        entry_date=body.entry_date,
        billable=body.billable,
    )
    return _entry_to_response(entry)


# ---------------------------------------------------------------------------
# DELETE .../time/{entry_id} — Delete time entry
# ---------------------------------------------------------------------------


@router.delete("/{entry_id}", status_code=204)
async def delete_time_entry(
    firm_id: UUID,
    matter_id: UUID,
    entry_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a time entry. Only the author can delete their own entries."""
    _require_time_entry(stakeholder)
    await time_tracking_service.delete_time_entry(
        db,
        entry_id=entry_id,
        matter_id=matter_id,
        stakeholder=stakeholder,
        current_user=current_user,
    )
