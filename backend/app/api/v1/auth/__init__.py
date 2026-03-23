"""Auth API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_db
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import get_current_user
from app.models.enums import InviteStatus
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.models.users import User
from app.schemas.auth import CurrentUser

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas specific to auth routes
# ---------------------------------------------------------------------------


class FirmMembershipDetail(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

    firm_id: UUID
    firm_name: str
    firm_slug: str
    firm_role: str


class UserProfile(BaseModel):
    """Full user profile with firm memberships."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    user_id: UUID
    email: str
    full_name: str
    firm_memberships: list[FirmMembershipDetail]


class AcceptInviteRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    invite_token: str


class AcceptInviteResponse(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

    stakeholder_id: UUID
    matter_id: UUID
    matter_title: str
    role: str


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserProfile)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    """Return current user profile with firm memberships.

    If this is the user's first login, the User record was already created
    by the get_current_user dependency (auto-provisioning).
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.firm_memberships).selectinload(FirmMembership.firm))
        .where(User.id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError(detail="User not found")

    memberships = []
    for m in user.firm_memberships:
        memberships.append(
            FirmMembershipDetail(
                firm_id=m.firm_id,
                firm_name=m.firm.name if m.firm else "",
                firm_slug=m.firm.slug if m.firm else "",
                firm_role=m.firm_role.value,
            )
        )

    return UserProfile(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        firm_memberships=memberships,
    )


# ---------------------------------------------------------------------------
# POST /auth/accept-invite
# ---------------------------------------------------------------------------


@router.post("/accept-invite", response_model=AcceptInviteResponse)
async def accept_invite(
    body: AcceptInviteRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AcceptInviteResponse:
    """Accept a stakeholder invitation.

    Links the authenticated user to the stakeholder record,
    updates invite_status to 'accepted', and returns the matter info.
    """
    result = await db.execute(
        select(Stakeholder)
        .options(selectinload(Stakeholder.matter))
        .where(Stakeholder.invite_token == body.invite_token)
    )
    stakeholder = result.scalar_one_or_none()

    if stakeholder is None:
        raise NotFoundError(detail="Invalid or expired invitation")

    if stakeholder.invite_status == InviteStatus.accepted:
        raise ConflictError(detail="Invitation has already been accepted")

    if stakeholder.invite_status == InviteStatus.revoked:
        raise NotFoundError(detail="Invitation has been revoked")

    # Link the user to the stakeholder record
    stakeholder.user_id = current_user.user_id
    stakeholder.invite_status = InviteStatus.accepted
    stakeholder.email = current_user.email

    await db.flush()

    return AcceptInviteResponse(
        stakeholder_id=stakeholder.id,
        matter_id=stakeholder.matter_id,
        matter_title=stakeholder.matter.title if stakeholder.matter else "",
        role=stakeholder.role.value,
    )
