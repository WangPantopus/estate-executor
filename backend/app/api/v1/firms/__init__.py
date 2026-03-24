"""Firm management API routes."""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.security import get_current_user, require_firm_member
from app.models.enums import FirmRole
from app.models.firm_memberships import FirmMembership
from app.schemas.auth import CurrentUser
from app.schemas.common import PaginationMeta, PaginationParams
from app.schemas.firms import FirmCreate, FirmListResponse, FirmResponse, FirmUpdate
from app.services import firm_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Member schemas (route-local — not part of the shared schema layer)
# ---------------------------------------------------------------------------


class FirmMemberResponse(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    firm_id: UUID
    user_id: UUID
    email: str
    full_name: str
    firm_role: str


class FirmMemberListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    data: list[FirmMemberResponse]
    meta: PaginationMeta


class InviteMemberRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    email: EmailStr
    full_name: str
    firm_role: FirmRole


class UpdateMemberRoleRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    firm_role: FirmRole


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _member_to_response(m: FirmMembership) -> FirmMemberResponse:
    return FirmMemberResponse(
        id=m.id,
        firm_id=m.firm_id,
        user_id=m.user_id,
        email=m.user.email if m.user else "",
        full_name=m.user.full_name if m.user else "",
        firm_role=m.firm_role.value,
    )


# ---------------------------------------------------------------------------
# POST /firms — Create a new firm
# ---------------------------------------------------------------------------


@router.post("", response_model=FirmResponse, status_code=201)
async def create_firm(
    body: FirmCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FirmResponse:
    """Create a new firm. The current user becomes the owner."""
    firm = await firm_service.create_firm(
        db,
        name=body.name,
        firm_type=body.type,
        current_user=current_user,
    )
    return FirmResponse.model_validate(firm)


# ---------------------------------------------------------------------------
# GET /firms — List firms the current user belongs to
# ---------------------------------------------------------------------------


@router.get("", response_model=FirmListResponse)
async def list_firms(
    current_user: CurrentUser = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> FirmListResponse:
    """List all firms the current user belongs to."""
    firms, total = await firm_service.list_user_firms(
        db,
        current_user=current_user,
        page=pagination.page,
        per_page=pagination.per_page,
    )
    return FirmListResponse(
        data=[FirmResponse.model_validate(f) for f in firms],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0,
        ),
    )


# ---------------------------------------------------------------------------
# GET /firms/{firm_id} — Get firm details
# ---------------------------------------------------------------------------


@router.get("/{firm_id}", response_model=FirmResponse)
async def get_firm(
    firm_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> FirmResponse:
    """Get firm details. Requires firm membership."""
    firm = await firm_service.get_firm(db, firm_id=firm_id)
    return FirmResponse.model_validate(firm)


# ---------------------------------------------------------------------------
# PATCH /firms/{firm_id} — Update firm
# ---------------------------------------------------------------------------


@router.patch("/{firm_id}", response_model=FirmResponse)
async def update_firm(
    firm_id: UUID,
    body: FirmUpdate,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FirmResponse:
    """Update firm details. Requires owner or admin role."""
    updates = body.model_dump(exclude_unset=True)
    firm = await firm_service.update_firm(
        db,
        firm_id=firm_id,
        updates=updates,
        current_user=current_user,
        membership=membership,
    )
    return FirmResponse.model_validate(firm)


# ---------------------------------------------------------------------------
# GET /firms/{firm_id}/members — List firm members
# ---------------------------------------------------------------------------


@router.get("/{firm_id}/members", response_model=FirmMemberListResponse)
async def list_members(
    firm_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> FirmMemberListResponse:
    """List all members of a firm. Requires firm membership."""
    members, total = await firm_service.list_firm_members(
        db,
        firm_id=firm_id,
        page=pagination.page,
        per_page=pagination.per_page,
    )
    return FirmMemberListResponse(
        data=[_member_to_response(m) for m in members],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0,
        ),
    )


# ---------------------------------------------------------------------------
# POST /firms/{firm_id}/members — Invite a firm member
# ---------------------------------------------------------------------------


@router.post("/{firm_id}/members", response_model=FirmMemberResponse, status_code=201)
async def invite_member(
    firm_id: UUID,
    body: InviteMemberRequest,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FirmMemberResponse:
    """Invite a new member to a firm. Requires owner or admin role."""
    from app.services.billing_service import check_user_limit

    await check_user_limit(db, firm_id)

    new_membership = await firm_service.invite_firm_member(
        db,
        firm_id=firm_id,
        email=body.email,
        full_name=body.full_name,
        firm_role=body.firm_role,
        current_user=current_user,
        membership=membership,
    )
    return _member_to_response(new_membership)


# ---------------------------------------------------------------------------
# PATCH /firms/{firm_id}/members/{membership_id} — Update member role
# ---------------------------------------------------------------------------


@router.patch("/{firm_id}/members/{membership_id}", response_model=FirmMemberResponse)
async def update_member_role(
    firm_id: UUID,
    membership_id: UUID,
    body: UpdateMemberRoleRequest,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FirmMemberResponse:
    """Update a member's role. Requires owner role."""
    updated = await firm_service.update_member_role(
        db,
        firm_id=firm_id,
        membership_id=membership_id,
        new_role=body.firm_role,
        current_user=current_user,
        current_membership=membership,
    )
    return _member_to_response(updated)


# ---------------------------------------------------------------------------
# DELETE /firms/{firm_id}/members/{membership_id} — Remove member
# ---------------------------------------------------------------------------


@router.delete("/{firm_id}/members/{membership_id}", status_code=204)
async def remove_member(
    firm_id: UUID,
    membership_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a member from a firm. Requires owner role. Cannot remove last owner."""
    await firm_service.remove_member(
        db,
        firm_id=firm_id,
        membership_id=membership_id,
        current_user=current_user,
        current_membership=membership,
    )
