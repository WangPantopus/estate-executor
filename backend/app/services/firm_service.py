"""Firm business logic service layer."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.events import event_logger
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models.enums import ActorType, FirmRole
from app.models.firm_memberships import FirmMembership
from app.models.firms import Firm
from app.models.users import User
from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """Convert a firm name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


async def _unique_slug(db: AsyncSession, base_slug: str) -> str:
    """Generate a unique slug, appending a number if collision exists."""
    slug = base_slug
    counter = 1
    while True:
        result = await db.execute(select(Firm.id).where(Firm.slug == slug))
        if result.scalar_one_or_none() is None:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


async def create_firm(
    db: AsyncSession,
    *,
    name: str,
    firm_type: str,
    current_user: CurrentUser,
) -> Firm:
    """Create a new firm and make the current user its owner."""
    base_slug = _slugify(name)
    if not base_slug:
        base_slug = "firm"
    slug = await _unique_slug(db, base_slug)

    firm = Firm(name=name, slug=slug, type=firm_type)
    db.add(firm)
    await db.flush()

    membership = FirmMembership(
        firm_id=firm.id,
        user_id=current_user.user_id,
        firm_role=FirmRole.owner,
    )
    db.add(membership)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=firm.id,  # Use firm_id as matter_id for firm-level events
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="firm",
        entity_id=firm.id,
        action="created",
        metadata={"name": name, "slug": slug, "type": firm_type},
    )

    return firm


async def list_user_firms(
    db: AsyncSession,
    *,
    current_user: CurrentUser,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[Firm], int]:
    """List all firms the current user belongs to."""
    count_q = (
        select(func.count())
        .select_from(FirmMembership)
        .where(FirmMembership.user_id == current_user.user_id)
    )
    total = (await db.execute(count_q)).scalar_one()

    q = (
        select(Firm)
        .join(FirmMembership, Firm.id == FirmMembership.firm_id)
        .where(FirmMembership.user_id == current_user.user_id)
        .order_by(Firm.name)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    return list(result.scalars().all()), total


async def get_firm(db: AsyncSession, *, firm_id: uuid.UUID) -> Firm:
    """Get a firm by ID. Raises NotFoundError if not found."""
    result = await db.execute(select(Firm).where(Firm.id == firm_id))
    firm = result.scalar_one_or_none()
    if firm is None:
        raise NotFoundError(detail="Firm not found")
    return firm


async def update_firm(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    updates: dict[str, Any],
    current_user: CurrentUser,
    membership: FirmMembership,
) -> Firm:
    """Update a firm. Requires owner or admin role."""
    if membership.firm_role not in (FirmRole.owner, FirmRole.admin):
        raise PermissionDeniedError(detail="Only owners and admins can update the firm")

    firm = await get_firm(db, firm_id=firm_id)

    changes: dict[str, Any] = {}
    for field, value in updates.items():
        if value is not None:
            old_value = getattr(firm, field, None)
            if old_value != value:
                changes[field] = {"old": str(old_value) if old_value is not None else None, "new": str(value)}
                setattr(firm, field, value)

    if changes:
        await db.flush()
        await event_logger.log(
            db,
            matter_id=firm.id,
            actor_id=current_user.user_id,
            actor_type=ActorType.user,
            entity_type="firm",
            entity_id=firm.id,
            action="updated",
            changes=changes,
        )

    return firm


async def list_firm_members(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[FirmMembership], int]:
    """List all members of a firm."""
    count_q = (
        select(func.count())
        .select_from(FirmMembership)
        .where(FirmMembership.firm_id == firm_id)
    )
    total = (await db.execute(count_q)).scalar_one()

    q = (
        select(FirmMembership)
        .options(selectinload(FirmMembership.user))
        .where(FirmMembership.firm_id == firm_id)
        .order_by(FirmMembership.created_at)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    return list(result.scalars().all()), total


async def invite_firm_member(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    email: str,
    full_name: str,
    firm_role: FirmRole,
    current_user: CurrentUser,
    membership: FirmMembership,
) -> FirmMembership:
    """Invite a new member to a firm. Requires owner or admin role."""
    if membership.firm_role not in (FirmRole.owner, FirmRole.admin):
        raise PermissionDeniedError(detail="Only owners and admins can invite members")

    # Find or create user by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        # Create a placeholder user — will be fully provisioned on first login
        user = User(
            auth_provider_id=f"pending:{uuid.uuid4()}",
            email=email,
            full_name=full_name,
        )
        db.add(user)
        await db.flush()

    # Check for existing membership
    result = await db.execute(
        select(FirmMembership).where(
            FirmMembership.firm_id == firm_id,
            FirmMembership.user_id == user.id,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise ConflictError(detail="User is already a member of this firm")

    new_membership = FirmMembership(
        firm_id=firm_id,
        user_id=user.id,
        firm_role=firm_role,
    )
    db.add(new_membership)
    await db.flush()

    # Reload with user relationship
    result = await db.execute(
        select(FirmMembership)
        .options(selectinload(FirmMembership.user))
        .where(FirmMembership.id == new_membership.id)
    )
    new_membership = result.scalar_one()

    await event_logger.log(
        db,
        matter_id=firm_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="firm_membership",
        entity_id=new_membership.id,
        action="created",
        metadata={"email": email, "firm_role": firm_role.value},
    )

    # Stub: log invitation email
    logger.info(
        "invitation_email_stub",
        extra={"firm_id": str(firm_id), "email": email, "role": firm_role.value},
    )

    return new_membership


async def update_member_role(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    membership_id: uuid.UUID,
    new_role: FirmRole,
    current_user: CurrentUser,
    current_membership: FirmMembership,
) -> FirmMembership:
    """Update a member's role. Requires owner role."""
    if current_membership.firm_role != FirmRole.owner:
        raise PermissionDeniedError(detail="Only owners can change member roles")

    result = await db.execute(
        select(FirmMembership)
        .options(selectinload(FirmMembership.user))
        .where(
            FirmMembership.id == membership_id,
            FirmMembership.firm_id == firm_id,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise NotFoundError(detail="Membership not found")

    old_role = target.firm_role.value
    target.firm_role = new_role
    await db.flush()

    await event_logger.log(
        db,
        matter_id=firm_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="firm_membership",
        entity_id=target.id,
        action="updated",
        changes={"firm_role": {"old": old_role, "new": new_role.value}},
    )

    return target


async def remove_member(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    membership_id: uuid.UUID,
    current_user: CurrentUser,
    current_membership: FirmMembership,
) -> None:
    """Remove a member from a firm. Requires owner role. Cannot remove last owner."""
    if current_membership.firm_role != FirmRole.owner:
        raise PermissionDeniedError(detail="Only owners can remove members")

    result = await db.execute(
        select(FirmMembership)
        .options(selectinload(FirmMembership.user))
        .where(
            FirmMembership.id == membership_id,
            FirmMembership.firm_id == firm_id,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise NotFoundError(detail="Membership not found")

    # Prevent removing the last owner
    if target.firm_role == FirmRole.owner:
        count_q = (
            select(func.count())
            .select_from(FirmMembership)
            .where(
                FirmMembership.firm_id == firm_id,
                FirmMembership.firm_role == FirmRole.owner,
            )
        )
        owner_count = (await db.execute(count_q)).scalar_one()
        if owner_count <= 1:
            raise ConflictError(detail="Cannot remove the last owner of the firm")

    await event_logger.log(
        db,
        matter_id=firm_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="firm_membership",
        entity_id=target.id,
        action="deleted",
        metadata={
            "email": target.user.email if target.user else None,
            "firm_role": target.firm_role.value,
        },
    )

    await db.delete(target)
    await db.flush()
