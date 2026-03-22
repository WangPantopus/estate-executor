"""Communication business logic — CRUD, visibility filtering, acknowledgements, disputes."""

from __future__ import annotations

import logging
import math
import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.events import event_logger
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.communications import Communication
from app.models.enums import (
    ActorType,
    CommunicationType,
    CommunicationVisibility,
    StakeholderRole,
)
from app.models.stakeholders import Stakeholder
from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

# Roles that can see professionals_only messages
_PROFESSIONAL_ROLES = {StakeholderRole.matter_admin, StakeholderRole.professional}

# Communication types that trigger email notification stubs
_EMAIL_TYPES = {
    CommunicationType.milestone_notification,
    CommunicationType.distribution_notice,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_communication_or_404(
    db: AsyncSession, *, comm_id: uuid.UUID, matter_id: uuid.UUID
) -> Communication:
    result = await db.execute(
        select(Communication)
        .options(selectinload(Communication.sender))
        .where(Communication.id == comm_id, Communication.matter_id == matter_id)
    )
    comm = result.scalar_one_or_none()
    if comm is None:
        raise NotFoundError(detail="Communication not found")
    return comm


async def _get_matter_admins(
    db: AsyncSession, *, matter_id: uuid.UUID
) -> list[Stakeholder]:
    """Return all stakeholders with matter_admin role for a matter."""
    result = await db.execute(
        select(Stakeholder).where(
            Stakeholder.matter_id == matter_id,
            Stakeholder.role == StakeholderRole.matter_admin,
        )
    )
    return list(result.scalars().all())


def _notify_email_stub(
    comm: Communication, recipients: list[Stakeholder]
) -> None:
    """Stub: log that an email would be sent for milestone/distribution notices."""
    logger.info(
        "email_notification_stub",
        extra={
            "communication_id": str(comm.id),
            "type": comm.type.value,
            "recipient_count": len(recipients),
            "recipient_ids": [str(s.id) for s in recipients],
        },
    )


# ---------------------------------------------------------------------------
# Create communication
# ---------------------------------------------------------------------------


async def create_communication(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    sender: Stakeholder,
    comm_type: CommunicationType,
    subject: str | None = None,
    body: str,
    visibility: CommunicationVisibility = CommunicationVisibility.all_stakeholders,
    visible_to: list[uuid.UUID] | None = None,
    current_user: CurrentUser,
) -> Communication:
    """Create a communication. Sender is set from the authenticated stakeholder."""
    # Ensure sender is always in visible_to for specific visibility
    if visibility == CommunicationVisibility.specific and visible_to is not None:
        if sender.id not in visible_to:
            visible_to = [sender.id, *visible_to]

    comm = Communication(
        matter_id=matter_id,
        sender_id=sender.id,
        type=comm_type,
        subject=subject,
        body=body,
        visibility=visibility,
        visible_to=visible_to if visibility == CommunicationVisibility.specific else None,
        acknowledged_by=[],
    )
    db.add(comm)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="communication",
        entity_id=comm.id,
        action="created",
        metadata={
            "type": comm_type.value,
            "visibility": visibility.value,
            "subject": subject,
        },
    )

    # Email notification stub for milestone/distribution types
    if comm_type in _EMAIL_TYPES:
        all_stakeholders = (
            await db.execute(
                select(Stakeholder).where(Stakeholder.matter_id == matter_id)
            )
        ).scalars().all()
        _notify_email_stub(comm, list(all_stakeholders))

    # Reload with sender relationship
    return await _get_communication_or_404(db, comm_id=comm.id, matter_id=matter_id)


# ---------------------------------------------------------------------------
# List communications (role-based visibility filtering)
# ---------------------------------------------------------------------------


async def list_communications(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    stakeholder: Stakeholder,
    comm_type: CommunicationType | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[Communication], int]:
    """List communications with role-based visibility filtering.

    Visibility rules:
    - matter_admin/professional: see all visibilities
    - executor_trustee: all_stakeholders + specific (if in visible_to)
    - beneficiary/read_only: all_stakeholders + specific (if in visible_to),
      EXCLUDING professionals_only
    """
    base_filters: list[Any] = [Communication.matter_id == matter_id]

    if comm_type is not None:
        base_filters.append(Communication.type == comm_type)

    # Build visibility filter based on role
    if stakeholder.role in _PROFESSIONAL_ROLES:
        # Admin/professional see everything
        visibility_filter = True  # no extra filter
    else:
        # Non-professionals: all_stakeholders + specific where they're in visible_to
        vis_conditions = [
            Communication.visibility == CommunicationVisibility.all_stakeholders,
        ]
        # Add specific visibility if they're in the visible_to array
        if stakeholder.id is not None:
            vis_conditions.append(
                (Communication.visibility == CommunicationVisibility.specific)
                & Communication.visible_to.any(stakeholder.id)
            )
        visibility_filter = or_(*vis_conditions)

    # Count query
    count_q = select(func.count()).select_from(Communication).where(*base_filters)
    if visibility_filter is not True:
        count_q = count_q.where(visibility_filter)
    total = (await db.execute(count_q)).scalar_one()

    # Data query
    q = (
        select(Communication)
        .options(selectinload(Communication.sender))
        .where(*base_filters)
    )
    if visibility_filter is not True:
        q = q.where(visibility_filter)

    q = (
        q.order_by(Communication.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    comms = list(result.scalars().unique().all())

    return comms, total


# ---------------------------------------------------------------------------
# Acknowledge distribution notice
# ---------------------------------------------------------------------------


async def acknowledge_communication(
    db: AsyncSession,
    *,
    comm_id: uuid.UUID,
    matter_id: uuid.UUID,
    stakeholder: Stakeholder,
    current_user: CurrentUser,
) -> Communication:
    """Acknowledge a distribution notice. Appends stakeholder to acknowledged_by."""
    comm = await _get_communication_or_404(db, comm_id=comm_id, matter_id=matter_id)

    if comm.type != CommunicationType.distribution_notice:
        raise PermissionDeniedError(
            detail="Only distribution notices can be acknowledged"
        )

    # Append (not replace) — idempotent
    current_acks = list(comm.acknowledged_by or [])
    if stakeholder.id not in current_acks:
        current_acks.append(stakeholder.id)
        comm.acknowledged_by = current_acks
        await db.flush()

        await event_logger.log(
            db,
            matter_id=matter_id,
            actor_id=current_user.user_id,
            actor_type=ActorType.user,
            entity_type="communication",
            entity_id=comm.id,
            action="acknowledged",
            metadata={
                "stakeholder_id": str(stakeholder.id),
                "stakeholder_name": stakeholder.full_name,
            },
        )

    return comm


# ---------------------------------------------------------------------------
# Create dispute flag
# ---------------------------------------------------------------------------


async def create_dispute_flag(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    sender: Stakeholder,
    entity_type: str,
    entity_id: uuid.UUID,
    reason: str,
    current_user: CurrentUser,
) -> Communication:
    """Create a dispute flag communication and notify all matter admins."""
    subject = f"Dispute: {entity_type} {entity_id}"

    comm = Communication(
        matter_id=matter_id,
        sender_id=sender.id,
        type=CommunicationType.dispute_flag,
        subject=subject,
        body=reason,
        visibility=CommunicationVisibility.all_stakeholders,
        visible_to=None,
        acknowledged_by=[],
    )
    db.add(comm)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="communication",
        entity_id=comm.id,
        action="dispute_flagged",
        metadata={
            "disputed_entity_type": entity_type,
            "disputed_entity_id": str(entity_id),
            "reason": reason,
        },
    )

    # Immediate notification to all matter admins
    admins = await _get_matter_admins(db, matter_id=matter_id)
    if admins:
        logger.info(
            "dispute_flag_admin_notification",
            extra={
                "communication_id": str(comm.id),
                "matter_id": str(matter_id),
                "admin_count": len(admins),
                "admin_ids": [str(a.id) for a in admins],
                "disputed_entity_type": entity_type,
                "disputed_entity_id": str(entity_id),
            },
        )
        _notify_email_stub(comm, admins)

    # Reload with sender relationship
    return await _get_communication_or_404(db, comm_id=comm.id, matter_id=matter_id)
