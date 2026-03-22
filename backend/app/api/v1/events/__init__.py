"""Event log / audit trail API routes — READ-ONLY."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.security import require_firm_member, require_stakeholder
from app.models.enums import StakeholderRole
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.schemas.events import CursorMeta, EventListResponse, EventResponse
from app.services import event_service

router = APIRouter()


def _event_to_response(event, actor_names: dict) -> EventResponse:
    """Convert an Event ORM object to EventResponse."""
    actor_name = None
    if event.actor_id is not None:
        actor_name = actor_names.get(event.actor_id)
    if actor_name is None and event.actor_type is not None:
        actor_name = event.actor_type.value  # fallback: "system", "ai"

    return EventResponse(
        id=event.id,
        matter_id=event.matter_id,
        actor_id=event.actor_id,
        actor_type=event.actor_type,
        actor_name=actor_name,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        action=event.action,
        changes=event.changes,
        metadata=event.metadata_,
        created_at=event.created_at,
    )


# ---------------------------------------------------------------------------
# GET .../events — List events (cursor-based pagination)
# ---------------------------------------------------------------------------


@router.get("", response_model=EventListResponse)
async def list_events(
    firm_id: UUID,
    matter_id: UUID,
    entity_type: str | None = Query(None),
    entity_id: UUID | None = Query(None),
    actor_id: UUID | None = Query(None),
    action: str | None = Query(None),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    cursor: str | None = Query(None, description="Cursor for pagination (created_at ISO timestamp)"),
    per_page: int = Query(50, ge=1, le=200),
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> EventListResponse:
    """Query events with filters. Cursor-based pagination, newest first.

    Beneficiaries and read_only users cannot access the audit log.
    """
    if _stakeholder.role in (StakeholderRole.beneficiary, StakeholderRole.read_only):
        raise PermissionDeniedError(detail="Insufficient permissions")
    events, actor_names, next_cursor = await event_service.list_events(
        db,
        matter_id=matter_id,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
        cursor=cursor,
        per_page=per_page,
    )
    return EventListResponse(
        data=[_event_to_response(e, actor_names) for e in events],
        meta=CursorMeta(
            has_more=next_cursor is not None,
            next_cursor=next_cursor,
            per_page=per_page,
        ),
    )


# ---------------------------------------------------------------------------
# GET .../events/export — CSV export (matter_admin only)
# ---------------------------------------------------------------------------


@router.get("/export")
async def export_events(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export all events for a matter as CSV. Requires matter_admin permission."""
    if stakeholder.role != StakeholderRole.matter_admin:
        raise PermissionDeniedError(
            detail="Only matter admins can export event logs"
        )

    csv_content = await event_service.export_events_csv(db, matter_id=matter_id)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=events_{matter_id}.csv"
        },
    )
