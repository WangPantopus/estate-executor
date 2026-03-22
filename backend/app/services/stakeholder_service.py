"""Stakeholder business logic service layer."""

from __future__ import annotations

import logging
import secrets
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.events import event_logger
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.enums import ActorType, InviteStatus, StakeholderRole
from app.models.matters import Matter
from app.models.stakeholders import Stakeholder
from app.models.users import User
from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

# Roles visible to beneficiaries when listing stakeholders
_BENEFICIARY_VISIBLE_ROLES = {StakeholderRole.beneficiary, StakeholderRole.professional}


def _generate_invite_token() -> str:
    """Generate a URL-safe random string, 48 characters."""
    return secrets.token_urlsafe(36)[:48]


async def _get_matter_or_404(db: AsyncSession, matter_id: uuid.UUID) -> Matter:
    """Fetch matter by ID or raise 404."""
    result = await db.execute(select(Matter).where(Matter.id == matter_id))
    matter = result.scalar_one_or_none()
    if matter is None:
        raise NotFoundError(detail="Matter not found")
    return matter


async def invite_stakeholder(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    email: str,
    full_name: str,
    role: StakeholderRole,
    relationship: str | None = None,
    current_user: CurrentUser,
) -> Stakeholder:
    """Invite a stakeholder to a matter.

    - Generates a unique invite_token
    - Returns 409 if email already a stakeholder on this matter
    - Auto-links user_id if email matches an existing user
    - Dispatches invitation email via Celery
    - Logs event
    """
    matter = await _get_matter_or_404(db, matter_id)

    # Check for duplicate email on this matter
    result = await db.execute(
        select(Stakeholder).where(
            Stakeholder.matter_id == matter_id,
            Stakeholder.email == email,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise ConflictError(detail="A stakeholder with this email already exists on this matter")

    # Check if email matches an existing user
    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalar_one_or_none()

    invite_token = _generate_invite_token()

    stakeholder = Stakeholder(
        matter_id=matter_id,
        user_id=existing_user.id if existing_user else None,
        email=email,
        full_name=full_name,
        role=role,
        relationship_label=relationship,
        invite_status=InviteStatus.accepted if existing_user else InviteStatus.pending,
        invite_token=None if existing_user else invite_token,
    )
    db.add(stakeholder)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="stakeholder",
        entity_id=stakeholder.id,
        action="created",
        metadata={
            "email": email,
            "role": role.value,
            "auto_linked": existing_user is not None,
        },
    )

    # Dispatch invitation email (Celery stub)
    _dispatch_invite_email(
        email=email,
        full_name=full_name,
        role=role,
        decedent_name=matter.decedent_name,
        invite_token=invite_token if not existing_user else None,
    )

    return stakeholder


async def list_stakeholders(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    viewer_role: StakeholderRole,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[Stakeholder], int]:
    """List stakeholders on a matter.

    Beneficiaries only see other beneficiaries and professionals.
    """
    base_filter = [Stakeholder.matter_id == matter_id]

    # Beneficiaries see limited stakeholder list
    if viewer_role == StakeholderRole.beneficiary:
        base_filter.append(Stakeholder.role.in_(_BENEFICIARY_VISIBLE_ROLES))

    count_q = (
        select(func.count())
        .select_from(Stakeholder)
        .where(*base_filter)
    )
    total = (await db.execute(count_q)).scalar_one()

    q = (
        select(Stakeholder)
        .where(*base_filter)
        .order_by(Stakeholder.created_at)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    return list(result.scalars().all()), total


async def get_stakeholder(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    stakeholder_id: uuid.UUID,
) -> Stakeholder:
    """Get a stakeholder by ID on a specific matter. Raises 404 if not found."""
    result = await db.execute(
        select(Stakeholder).where(
            Stakeholder.id == stakeholder_id,
            Stakeholder.matter_id == matter_id,
        )
    )
    stakeholder = result.scalar_one_or_none()
    if stakeholder is None:
        raise NotFoundError(detail="Stakeholder not found")
    return stakeholder


async def update_stakeholder(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    stakeholder_id: uuid.UUID,
    updates: dict[str, Any],
    current_user: CurrentUser,
) -> Stakeholder:
    """Update a stakeholder's role, relationship, or notification_preferences."""
    stakeholder = await get_stakeholder(db, matter_id=matter_id, stakeholder_id=stakeholder_id)

    # Map schema field names to model attribute names
    field_map = {"relationship": "relationship_label"}

    changes: dict[str, Any] = {}
    for field, value in updates.items():
        attr = field_map.get(field, field)
        old_value = getattr(stakeholder, attr, None)
        # Normalize enum comparison
        old_cmp = old_value.value if hasattr(old_value, "value") else old_value
        new_cmp = value.value if hasattr(value, "value") else value
        if old_cmp != new_cmp:
            changes[field] = {"old": old_cmp, "new": new_cmp}
            setattr(stakeholder, attr, value)

    if changes:
        await db.flush()
        await event_logger.log(
            db,
            matter_id=matter_id,
            actor_id=current_user.user_id,
            actor_type=ActorType.user,
            entity_type="stakeholder",
            entity_id=stakeholder.id,
            action="updated",
            changes=changes,
        )

    return stakeholder


async def remove_stakeholder(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    stakeholder_id: uuid.UUID,
    current_user: CurrentUser,
) -> None:
    """Remove a stakeholder. Cannot remove the last matter_admin."""
    stakeholder = await get_stakeholder(db, matter_id=matter_id, stakeholder_id=stakeholder_id)

    # Prevent removing the last matter_admin
    if stakeholder.role == StakeholderRole.matter_admin:
        count_q = (
            select(func.count())
            .select_from(Stakeholder)
            .where(
                Stakeholder.matter_id == matter_id,
                Stakeholder.role == StakeholderRole.matter_admin,
            )
        )
        admin_count = (await db.execute(count_q)).scalar_one()
        if admin_count <= 1:
            raise BadRequestError(detail="Cannot remove the last matter admin")

    # If invite is pending, mark as revoked before deletion
    if stakeholder.invite_status == InviteStatus.pending:
        stakeholder.invite_status = InviteStatus.revoked
        stakeholder.invite_token = None

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="stakeholder",
        entity_id=stakeholder.id,
        action="deleted",
        metadata={
            "email": stakeholder.email,
            "role": stakeholder.role.value,
        },
    )

    await db.delete(stakeholder)
    await db.flush()


async def resend_invite(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    stakeholder_id: uuid.UUID,
    current_user: CurrentUser,
) -> Stakeholder:
    """Re-send invitation email with a new invite_token."""
    stakeholder = await get_stakeholder(db, matter_id=matter_id, stakeholder_id=stakeholder_id)

    if stakeholder.invite_status != InviteStatus.pending:
        raise BadRequestError(
            detail="Can only resend invitations for pending stakeholders"
        )

    matter = await _get_matter_or_404(db, matter_id)

    # Generate new token (invalidates old one)
    new_token = _generate_invite_token()
    stakeholder.invite_token = new_token
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="stakeholder",
        entity_id=stakeholder.id,
        action="invite_resent",
        metadata={"email": stakeholder.email},
    )

    _dispatch_invite_email(
        email=stakeholder.email,
        full_name=stakeholder.full_name,
        role=stakeholder.role,
        decedent_name=matter.decedent_name,
        invite_token=new_token,
    )

    return stakeholder


# ---------------------------------------------------------------------------
# Email dispatch stub
# ---------------------------------------------------------------------------

_ROLE_DESCRIPTIONS: dict[StakeholderRole, str] = {
    StakeholderRole.matter_admin: "full administrative access to manage all aspects of the estate",
    StakeholderRole.professional: "professional access to manage tasks, assets, and communications",
    StakeholderRole.executor_trustee: "access to your assigned tasks, linked documents, and communications",
    StakeholderRole.beneficiary: "access to view estate milestones, shared documents, and communications relevant to you",
    StakeholderRole.read_only: "read-only access to view estate milestones",
}


def _dispatch_invite_email(
    *,
    email: str,
    full_name: str,
    role: StakeholderRole,
    decedent_name: str,
    invite_token: str | None,
) -> None:
    """Dispatch an invitation email via Celery (stub — logs content for now).

    In production this would call:
        send_stakeholder_invite_email.delay(email=email, ...)
    """
    invite_url = f"{settings.frontend_url}/invite/{invite_token}" if invite_token else None
    role_description = _ROLE_DESCRIPTIONS.get(role, "access to the estate")

    subject = f"You've been invited to Estate of {decedent_name}"
    body = (
        f"Dear {full_name},\n\n"
        f"You have been invited as a {role.value.replace('_', ' ')} "
        f"to the Estate of {decedent_name}.\n\n"
        f"As a {role.value.replace('_', ' ')}, you will have {role_description}.\n\n"
    )
    if invite_url:
        body += (
            f"Please click the link below to accept your invitation:\n"
            f"{invite_url}\n\n"
            f"[Accept Invitation]\n\n"
        )
    else:
        body += "Your account has been automatically linked. You can access the matter from your dashboard.\n\n"

    body += "If you have any questions, please contact the estate administrator."

    logger.info(
        "invitation_email_stub",
        extra={
            "to": email,
            "subject": subject,
            "body": body,
            "invite_url": invite_url,
            "role": role.value,
        },
    )
