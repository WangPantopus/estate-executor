"""Communication Center API routes."""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.security import get_current_user, require_firm_member, require_stakeholder
from app.models.communications import Communication
from app.models.enums import CommunicationType, CommunicationVisibility, StakeholderRole
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.schemas.auth import CurrentUser
from app.schemas.common import PaginationMeta, PaginationParams
from app.schemas.communications import (
    CommunicationCreate,
    CommunicationListResponse,
    CommunicationResponse,
    DisputeFlagCreate,
    DisputeStatusUpdate,
)
from app.services import communication_service

router = APIRouter()
dispute_flag_router = APIRouter()


def _comm_to_response(comm: Communication) -> CommunicationResponse:
    """Convert a Communication ORM object to CommunicationResponse."""
    return CommunicationResponse(
        id=comm.id,
        matter_id=comm.matter_id,
        sender_id=comm.sender_id,
        sender_name=comm.sender.full_name if comm.sender else "",
        type=comm.type,
        subject=comm.subject,
        body=comm.body,
        visibility=comm.visibility,
        acknowledged_by=comm.acknowledged_by,
        created_at=comm.created_at,
        # Dispute fields
        disputed_entity_type=comm.disputed_entity_type,
        disputed_entity_id=comm.disputed_entity_id,
        dispute_status=comm.dispute_status.value if comm.dispute_status else None,
        dispute_resolution_note=comm.dispute_resolution_note,
        dispute_resolved_at=comm.dispute_resolved_at,
        dispute_resolved_by=comm.dispute_resolved_by,
    )


# ---------------------------------------------------------------------------
# POST .../communications — Create communication
# ---------------------------------------------------------------------------


@router.post("", response_model=CommunicationResponse, status_code=201)
async def create_communication(
    firm_id: UUID,
    matter_id: UUID,
    body: CommunicationCreate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommunicationResponse:
    """Create a communication. Sender is automatically set to current stakeholder."""
    # Beneficiaries can only create with all_stakeholders visibility
    if (
        stakeholder.role == StakeholderRole.beneficiary
        and body.visibility
        and body.visibility != CommunicationVisibility.all_stakeholders
    ):
        raise PermissionDeniedError(detail="Beneficiaries can only send to all stakeholders")

    # Only professionals can use professionals_only visibility
    if body.visibility == CommunicationVisibility.professionals_only and stakeholder.role not in {
        StakeholderRole.matter_admin,
        StakeholderRole.professional,
    }:
        raise PermissionDeniedError(
            detail="Only matter admins and professionals can use professionals_only visibility"
        )

    comm = await communication_service.create_communication(
        db,
        matter_id=matter_id,
        sender=stakeholder,
        comm_type=body.type,
        subject=body.subject,
        body=body.body,
        visibility=body.visibility or CommunicationVisibility.all_stakeholders,
        visible_to=body.visible_to,
        current_user=current_user,
    )
    return _comm_to_response(comm)


# ---------------------------------------------------------------------------
# GET .../communications — List communications
# ---------------------------------------------------------------------------


@router.get("", response_model=CommunicationListResponse)
async def list_communications(
    firm_id: UUID,
    matter_id: UUID,
    type: CommunicationType | None = Query(None),  # noqa: A002
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> CommunicationListResponse:
    """List communications with role-based visibility filtering."""
    comms, total = await communication_service.list_communications(
        db,
        matter_id=matter_id,
        stakeholder=stakeholder,
        comm_type=type,
        page=pagination.page,
        per_page=pagination.per_page,
    )
    return CommunicationListResponse(
        data=[_comm_to_response(c) for c in comms],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0,
        ),
    )


# ---------------------------------------------------------------------------
# POST .../communications/{comm_id}/acknowledge
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# GET .../communications/disputes — List active disputes for a matter
# ---------------------------------------------------------------------------


@router.get("/disputes")
async def list_active_disputes(
    firm_id: UUID,
    matter_id: UUID,
    entity_type: str | None = Query(None),
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List entity IDs with active (non-resolved) disputes.

    Returns a map of entity_type → list of disputed entity_ids.
    Used by frontend to show "Disputed" badges on tasks/assets.
    """
    from sqlalchemy import select

    from app.models.enums import DisputeStatus

    filters = [
        Communication.matter_id == matter_id,
        Communication.type == CommunicationType.dispute_flag,
        Communication.dispute_status.in_([
            DisputeStatus.open,
            DisputeStatus.under_review,
        ]),
    ]
    if entity_type:
        filters.append(Communication.disputed_entity_type == entity_type)

    result = await db.execute(
        select(
            Communication.disputed_entity_type,
            Communication.disputed_entity_id,
            Communication.dispute_status,
        )
        .where(*filters)
        .distinct()
    )

    disputes: dict[str, list[dict]] = {}
    for row in result.all():
        etype = row[0] or "unknown"
        if etype not in disputes:
            disputes[etype] = []
        disputes[etype].append({
            "entity_id": str(row[1]) if row[1] else None,
            "dispute_status": row[2].value if row[2] else "open",
        })

    return {"disputes": disputes}


# ---------------------------------------------------------------------------
# POST .../communications/{comm_id}/acknowledge
# ---------------------------------------------------------------------------


@router.post("/{comm_id}/acknowledge", response_model=CommunicationResponse)
async def acknowledge_communication(
    firm_id: UUID,
    matter_id: UUID,
    comm_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommunicationResponse:
    """Acknowledge a distribution notice."""
    comm = await communication_service.acknowledge_communication(
        db,
        comm_id=comm_id,
        matter_id=matter_id,
        stakeholder=stakeholder,
        current_user=current_user,
    )
    return _comm_to_response(comm)


# ---------------------------------------------------------------------------
# POST .../dispute-flag — Create dispute flag
# ---------------------------------------------------------------------------


@dispute_flag_router.post("", response_model=CommunicationResponse, status_code=201)
async def create_dispute_flag(
    firm_id: UUID,
    matter_id: UUID,
    body: DisputeFlagCreate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommunicationResponse:
    """Flag a dispute on an entity. Notifies all matter admins immediately."""
    comm = await communication_service.create_dispute_flag(
        db,
        matter_id=matter_id,
        sender=stakeholder,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        reason=body.reason,
        current_user=current_user,
    )
    return _comm_to_response(comm)


# ---------------------------------------------------------------------------
# PUT .../dispute-flag/{comm_id} — Update dispute status
# ---------------------------------------------------------------------------


@dispute_flag_router.put("/{comm_id}", response_model=CommunicationResponse)
async def update_dispute_status(
    firm_id: UUID,
    matter_id: UUID,
    comm_id: UUID,
    body: DisputeStatusUpdate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommunicationResponse:
    """Update a dispute's status. Only matter admins can do this.

    Valid transitions: open → under_review, open → resolved, under_review → resolved.
    Resolution requires a note.
    """
    if stakeholder.role != StakeholderRole.matter_admin:
        raise PermissionDeniedError(detail="Only matter admins can update dispute status")

    comm = await communication_service.update_dispute_status(
        db,
        comm_id=comm_id,
        matter_id=matter_id,
        new_status=body.status,
        resolution_note=body.resolution_note,
        stakeholder=stakeholder,
        current_user=current_user,
    )
    return _comm_to_response(comm)
