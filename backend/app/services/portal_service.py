"""Beneficiary Portal service — read-only data for beneficiary users."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.communications import Communication
from app.models.documents import Document
from app.models.enums import (
    CommunicationType,
    CommunicationVisibility,
    MatterPhase,
    StakeholderRole,
    TaskStatus,
)
from app.models.firms import Firm
from app.models.matters import Matter
from app.models.stakeholders import Stakeholder
from app.models.tasks import Task

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

# Phase ordering for milestone computation
_PHASE_ORDER = [
    MatterPhase.immediate,
    MatterPhase.administration,
    MatterPhase.distribution,
    MatterPhase.closing,
]

_PHASE_LABELS = {
    MatterPhase.immediate: "Initial review",
    MatterPhase.administration: "Estate administration",
    MatterPhase.distribution: "Distribution",
    MatterPhase.closing: "Final closing",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_beneficiary_stakeholder(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Stakeholder:
    """Get the beneficiary stakeholder record, or raise 403."""
    result = await db.execute(
        select(Stakeholder).where(
            Stakeholder.matter_id == matter_id,
            Stakeholder.user_id == user_id,
        )
    )
    stakeholder = result.scalar_one_or_none()
    if stakeholder is None:
        raise NotFoundError(detail="Matter not found")
    if stakeholder.role != StakeholderRole.beneficiary:
        raise PermissionDeniedError(detail="Portal access requires beneficiary role")
    return stakeholder


# ---------------------------------------------------------------------------
# List beneficiary matters
# ---------------------------------------------------------------------------


async def list_beneficiary_matters(
    db: AsyncSession,
    *,
    current_user: CurrentUser,
) -> list[dict[str, Any]]:
    """Return all matters where user is a beneficiary stakeholder."""
    result = await db.execute(
        select(Stakeholder, Matter, Firm)
        .join(Matter, Stakeholder.matter_id == Matter.id)
        .join(Firm, Matter.firm_id == Firm.id)
        .where(
            Stakeholder.user_id == current_user.user_id,
            Stakeholder.role == StakeholderRole.beneficiary,
        )
    )
    rows = result.all()
    return [
        {
            "matter_id": matter.id,
            "firm_id": firm.id,
            "decedent_name": matter.decedent_name,
            "phase": matter.phase,
            "firm_name": firm.name,
        }
        for _stakeholder, matter, firm in rows
    ]


# ---------------------------------------------------------------------------
# Portal overview
# ---------------------------------------------------------------------------


async def get_portal_overview(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Build the portal overview response for a beneficiary."""
    stakeholder = await _get_beneficiary_stakeholder(
        db, matter_id=matter_id, user_id=current_user.user_id
    )

    # Load matter + firm
    result = await db.execute(
        select(Matter, Firm).join(Firm, Matter.firm_id == Firm.id).where(Matter.id == matter_id)
    )
    row = result.one_or_none()
    if row is None:
        raise NotFoundError(detail="Matter not found")
    matter, firm = row

    # Task summary for completion percentage
    task_result = await db.execute(
        select(
            func.count(Task.id).label("total"),
            func.count(Task.id).filter(Task.status == TaskStatus.complete).label("complete"),
        ).where(Task.matter_id == matter_id)
    )
    task_row = task_result.one()
    total_tasks = task_row.total or 0
    complete_tasks = task_row.complete or 0
    completion_pct = (complete_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Professional contacts (matter_admin and professional stakeholders)
    contact_result = await db.execute(
        select(Stakeholder).where(
            Stakeholder.matter_id == matter_id,
            Stakeholder.role.in_([StakeholderRole.matter_admin, StakeholderRole.professional]),
        )
    )
    contacts = [
        {
            "name": s.full_name,
            "email": s.email,
            "role": "Lead Attorney" if s.role == StakeholderRole.matter_admin else "Professional",
        }
        for s in contact_result.scalars().all()
    ]

    # Build milestones from events (milestone_notification communications)
    milestone_result = await db.execute(
        select(Communication)
        .where(
            Communication.matter_id == matter_id,
            Communication.type == CommunicationType.milestone_notification,
        )
        .order_by(Communication.created_at.asc())
    )
    milestone_comms = milestone_result.scalars().all()

    # Build milestones from phases and milestone events
    milestones = _build_milestones(matter, list(milestone_comms))

    # Distribution summary
    dist_result = await db.execute(
        select(func.count(Communication.id)).where(
            Communication.matter_id == matter_id,
            Communication.type == CommunicationType.distribution_notice,
        )
    )
    dist_count = dist_result.scalar() or 0

    # Count pending acknowledgments for this user
    pending_ack_result = await db.execute(
        select(func.count(Communication.id)).where(
            Communication.matter_id == matter_id,
            Communication.type == CommunicationType.distribution_notice,
            ~Communication.acknowledged_by.contains([current_user.user_id]),
        )
    )
    pending_acks = pending_ack_result.scalar() or 0

    dist_status = "pending"
    if matter.phase == MatterPhase.closing:
        dist_status = "completed"
    elif matter.phase == MatterPhase.distribution:
        dist_status = "in_progress"

    # Firm white_label config
    white_label = firm.settings.get("white_label", {}) if firm.settings else {}

    return {
        "matter": {
            "matter_id": matter.id,
            "decedent_name": matter.decedent_name,
            "estate_type": matter.estate_type,
            "jurisdiction_state": matter.jurisdiction_state,
            "phase": matter.phase,
            "completion_percentage": round(completion_pct, 1),
            "estimated_completion": None,
        },
        "your_role": "Beneficiary",
        "your_relationship": stakeholder.relationship_label,
        "contacts": contacts,
        "milestones": milestones,
        "distribution": {
            "total_estate_value": None,  # Only disclosed if professional enables it
            "distribution_status": dist_status,
            "notices_count": dist_count,
            "pending_acknowledgments": pending_acks,
        },
        "firm_name": firm.name,
        "firm_logo_url": white_label.get("logo_url"),
    }


def _build_milestones(matter: Matter, milestone_comms: list[Communication]) -> list[dict[str, Any]]:
    """Build milestone list from matter phase and milestone communications."""
    current_phase_idx = _PHASE_ORDER.index(matter.phase) if matter.phase in _PHASE_ORDER else 0
    milestones = []

    # Add phase-based milestones
    for i, phase in enumerate(_PHASE_ORDER):
        completed = i < current_phase_idx
        is_current = i == current_phase_idx
        milestones.append(
            {
                "title": _PHASE_LABELS.get(phase, str(phase)),
                "date": "",
                "completed": completed,
                "is_next": is_current and not completed,
            }
        )

    # Add actual milestone communications
    for comm in milestone_comms:
        milestones.append(
            {
                "title": comm.subject or "Milestone reached",
                "date": comm.created_at.strftime("%B %d, %Y"),
                "completed": True,
                "is_next": False,
            }
        )

    return milestones


# ---------------------------------------------------------------------------
# Portal documents
# ---------------------------------------------------------------------------


async def get_portal_documents(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Return documents shared with the beneficiary."""
    await _get_beneficiary_stakeholder(db, matter_id=matter_id, user_id=current_user.user_id)

    # Documents shared via communications visible to beneficiaries,
    # or documents with doc_type in shareable categories
    # For now, return documents that are linked to communications visible to beneficiaries
    # In practice, we return documents that have been explicitly shared (via distribution notices)
    # or have common shareable doc types
    shareable_types = {"death_certificate", "court_filing", "distribution_notice", "correspondence"}

    result = await db.execute(
        select(Document)
        .where(
            Document.matter_id == matter_id,
            or_(
                Document.doc_type.in_(shareable_types),
                Document.doc_type_confirmed.is_(True),
            ),
        )
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()

    # Filter to only confirmed shareable types
    shared_docs = [d for d in docs if d.doc_type in shareable_types]

    return {
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "doc_type": d.doc_type,
                "size_bytes": d.size_bytes,
                "shared_at": d.created_at,
            }
            for d in shared_docs
        ],
        "total": len(shared_docs),
    }


# ---------------------------------------------------------------------------
# Portal messages
# ---------------------------------------------------------------------------


async def get_portal_messages(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Return communications visible to the beneficiary."""
    stakeholder = await _get_beneficiary_stakeholder(
        db, matter_id=matter_id, user_id=current_user.user_id
    )

    # Beneficiaries see: all_stakeholders visibility, specific (if they're in visible_to),
    # and distribution_notices
    result = await db.execute(
        select(Communication)
        .options(selectinload(Communication.sender))
        .where(
            Communication.matter_id == matter_id,
            or_(
                Communication.visibility == CommunicationVisibility.all_stakeholders,
                Communication.type == CommunicationType.distribution_notice,
                Communication.type == CommunicationType.milestone_notification,
                and_(
                    Communication.visibility == CommunicationVisibility.specific,
                    Communication.visible_to.contains([stakeholder.id]),
                ),
            ),
            # Exclude professionals_only
            Communication.visibility != CommunicationVisibility.professionals_only,
        )
        .order_by(Communication.created_at.desc())
    )
    comms = result.scalars().all()

    return {
        "messages": [
            {
                "id": c.id,
                "sender_name": c.sender.full_name if c.sender else "System",
                "type": c.type,
                "subject": c.subject,
                "body": c.body,
                "created_at": c.created_at,
                "requires_acknowledgment": c.type == CommunicationType.distribution_notice,
                "acknowledged": (
                    current_user.user_id in (c.acknowledged_by or [])
                    if c.type == CommunicationType.distribution_notice
                    else False
                ),
            }
            for c in comms
        ],
        "total": len(comms),
    }


# ---------------------------------------------------------------------------
# Post message from beneficiary
# ---------------------------------------------------------------------------


async def post_beneficiary_message(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    current_user: CurrentUser,
    subject: str | None,
    body: str,
) -> dict[str, Any]:
    """Create a message from a beneficiary (visible to professionals)."""
    stakeholder = await _get_beneficiary_stakeholder(
        db, matter_id=matter_id, user_id=current_user.user_id
    )

    comm = Communication(
        matter_id=matter_id,
        sender_id=stakeholder.id,
        type=CommunicationType.message,
        subject=subject or "Message from beneficiary",
        body=body,
        visibility=CommunicationVisibility.all_stakeholders,
    )
    db.add(comm)
    await db.flush()

    return {
        "id": comm.id,
        "sender_name": stakeholder.full_name,
        "type": comm.type,
        "subject": comm.subject,
        "body": comm.body,
        "created_at": comm.created_at,
        "requires_acknowledgment": False,
        "acknowledged": False,
    }


# ---------------------------------------------------------------------------
# Acknowledge distribution notice
# ---------------------------------------------------------------------------


async def acknowledge_distribution_notice(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    communication_id: uuid.UUID,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Acknowledge a distribution notice."""
    await _get_beneficiary_stakeholder(db, matter_id=matter_id, user_id=current_user.user_id)

    result = await db.execute(
        select(Communication)
        .options(selectinload(Communication.sender))
        .where(
            Communication.id == communication_id,
            Communication.matter_id == matter_id,
            Communication.type == CommunicationType.distribution_notice,
        )
    )
    comm = result.scalar_one_or_none()
    if comm is None:
        raise NotFoundError(detail="Distribution notice not found")

    acknowledged = list(comm.acknowledged_by or [])
    if current_user.user_id not in acknowledged:
        acknowledged.append(current_user.user_id)
        comm.acknowledged_by = acknowledged
        await db.flush()

    return {
        "id": comm.id,
        "sender_name": comm.sender.full_name if comm.sender else "System",
        "type": comm.type,
        "subject": comm.subject,
        "body": comm.body,
        "created_at": comm.created_at,
        "requires_acknowledgment": True,
        "acknowledged": True,
    }
