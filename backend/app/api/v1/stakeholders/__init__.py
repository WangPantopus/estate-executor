"""Stakeholder management API routes."""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.security import (
    get_current_user,
    require_firm_member,
    require_permission,
    require_stakeholder,
)
from app.models.enums import StakeholderRole
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.schemas.auth import CurrentUser
from app.schemas.common import PaginationMeta, PaginationParams
from app.schemas.stakeholders import (
    StakeholderInvite,
    StakeholderListResponse,
    StakeholderResponse,
    StakeholderUpdate,
)
from app.services import stakeholder_service

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /stakeholders — Invite a stakeholder
# ---------------------------------------------------------------------------


@router.post("", response_model=StakeholderResponse, status_code=201)
async def invite_stakeholder(
    firm_id: UUID,
    matter_id: UUID,
    body: StakeholderInvite,
    _membership: FirmMembership = Depends(require_firm_member),
    _admin: Stakeholder = Depends(require_permission("stakeholder:manage")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StakeholderResponse:
    """Invite a stakeholder to a matter. Requires matter_admin permission."""
    stakeholder = await stakeholder_service.invite_stakeholder(
        db,
        matter_id=matter_id,
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        relationship=body.relationship,
        current_user=current_user,
    )
    return StakeholderResponse.model_validate(stakeholder)


# ---------------------------------------------------------------------------
# GET /stakeholders — List stakeholders
# ---------------------------------------------------------------------------


@router.get("", response_model=StakeholderListResponse)
async def list_stakeholders(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> StakeholderListResponse:
    """List stakeholders on a matter.

    Beneficiaries only see other beneficiaries and professionals.
    """
    items, total = await stakeholder_service.list_stakeholders(
        db,
        matter_id=matter_id,
        viewer_role=stakeholder.role,
        page=pagination.page,
        per_page=pagination.per_page,
    )
    return StakeholderListResponse(
        data=[StakeholderResponse.model_validate(s) for s in items],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0,
        ),
    )


# ---------------------------------------------------------------------------
# PATCH /stakeholders/{stakeholder_id} — Update stakeholder
# ---------------------------------------------------------------------------


@router.patch("/{stakeholder_id}", response_model=StakeholderResponse)
async def update_stakeholder(
    firm_id: UUID,
    matter_id: UUID,
    stakeholder_id: UUID,
    body: StakeholderUpdate,
    _membership: FirmMembership = Depends(require_firm_member),
    _admin: Stakeholder = Depends(require_permission("stakeholder:manage")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StakeholderResponse:
    """Update a stakeholder. Requires matter_admin permission."""
    updates = body.model_dump(exclude_unset=True)
    stakeholder = await stakeholder_service.update_stakeholder(
        db,
        matter_id=matter_id,
        stakeholder_id=stakeholder_id,
        updates=updates,
        current_user=current_user,
    )
    return StakeholderResponse.model_validate(stakeholder)


# ---------------------------------------------------------------------------
# DELETE /stakeholders/{stakeholder_id} — Remove stakeholder
# ---------------------------------------------------------------------------


@router.delete("/{stakeholder_id}", status_code=204)
async def remove_stakeholder(
    firm_id: UUID,
    matter_id: UUID,
    stakeholder_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    _admin: Stakeholder = Depends(require_permission("stakeholder:manage")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a stakeholder. Cannot remove the last matter_admin."""
    await stakeholder_service.remove_stakeholder(
        db,
        matter_id=matter_id,
        stakeholder_id=stakeholder_id,
        current_user=current_user,
    )


# ---------------------------------------------------------------------------
# POST /stakeholders/{stakeholder_id}/resend-invite — Resend invitation
# ---------------------------------------------------------------------------


@router.post("/{stakeholder_id}/resend-invite", response_model=StakeholderResponse)
async def resend_invite(
    firm_id: UUID,
    matter_id: UUID,
    stakeholder_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    _admin: Stakeholder = Depends(require_permission("stakeholder:manage")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StakeholderResponse:
    """Resend invitation email with a new invite_token."""
    stakeholder = await stakeholder_service.resend_invite(
        db,
        matter_id=matter_id,
        stakeholder_id=stakeholder_id,
        current_user=current_user,
    )
    return StakeholderResponse.model_validate(stakeholder)
