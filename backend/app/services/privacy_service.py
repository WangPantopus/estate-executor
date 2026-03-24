"""Privacy service — handles GDPR/CCPA data export and deletion requests."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.core.events import event_logger
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.communications import Communication
from app.models.enums import ActorType, PrivacyRequestStatus, PrivacyRequestType
from app.models.events import Event
from app.models.firm_memberships import FirmMembership
from app.models.privacy_requests import PrivacyRequest
from app.models.stakeholders import Stakeholder
from app.models.users import User

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

ANONYMIZED_NAME = "[Deleted User]"
ANONYMIZED_EMAIL = "deleted@anonymized.invalid"
ANONYMIZED_PHONE = None


# ---------------------------------------------------------------------------
# Create privacy request
# ---------------------------------------------------------------------------


async def create_request(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    user_id: uuid.UUID,
    request_type: PrivacyRequestType,
    reason: str | None = None,
) -> PrivacyRequest:
    """Create a new privacy request (data export or deletion)."""
    # Check for existing pending/processing request of the same type
    existing = await db.execute(
        select(PrivacyRequest).where(
            PrivacyRequest.user_id == user_id,
            PrivacyRequest.firm_id == firm_id,
            PrivacyRequest.request_type == request_type,
            PrivacyRequest.status.in_([
                PrivacyRequestStatus.pending,
                PrivacyRequestStatus.approved,
                PrivacyRequestStatus.processing,
            ]),
        )
    )
    if existing.scalar_one_or_none():
        from app.core.exceptions import ConflictError
        raise ConflictError(
            detail=f"A {request_type.value} request is already pending or in progress."
        )

    request = PrivacyRequest(
        firm_id=firm_id,
        user_id=user_id,
        request_type=request_type,
        reason=reason,
    )
    db.add(request)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=None,
        actor_id=user_id,
        actor_type=ActorType.user,
        entity_type="privacy_request",
        entity_id=request.id,
        action="created",
        metadata={
            "request_type": request_type.value,
            "reason": reason,
        },
    )

    return request


# ---------------------------------------------------------------------------
# List requests (for admin queue)
# ---------------------------------------------------------------------------


async def list_requests(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    status: PrivacyRequestStatus | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[PrivacyRequest], int]:
    """List privacy requests for a firm. Used by admins to manage the queue."""
    from sqlalchemy import func

    filters = [PrivacyRequest.firm_id == firm_id]
    if status:
        filters.append(PrivacyRequest.status == status)

    count_q = select(func.count()).select_from(PrivacyRequest).where(*filters)
    total = (await db.execute(count_q)).scalar_one()

    q = (
        select(PrivacyRequest)
        .options(selectinload(PrivacyRequest.user), selectinload(PrivacyRequest.reviewer))
        .where(*filters)
        .order_by(PrivacyRequest.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    requests = list(result.scalars().unique().all())
    return requests, total


# ---------------------------------------------------------------------------
# Get user's own requests
# ---------------------------------------------------------------------------


async def list_my_requests(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[PrivacyRequest]:
    """List privacy requests for the current user."""
    q = (
        select(PrivacyRequest)
        .where(PrivacyRequest.user_id == user_id)
        .order_by(PrivacyRequest.created_at.desc())
    )
    result = await db.execute(q)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Admin: approve / reject
# ---------------------------------------------------------------------------


async def review_request(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    firm_id: uuid.UUID,
    action: str,  # "approve" or "reject"
    reviewer_id: uuid.UUID,
    note: str | None = None,
) -> PrivacyRequest:
    """Admin approves or rejects a privacy request."""
    result = await db.execute(
        select(PrivacyRequest).where(
            PrivacyRequest.id == request_id,
            PrivacyRequest.firm_id == firm_id,
        )
    )
    request = result.scalar_one_or_none()
    if not request:
        raise NotFoundError(detail="Privacy request not found")

    if request.status != PrivacyRequestStatus.pending:
        raise PermissionDeniedError(
            detail=f"Cannot {action} a request with status '{request.status.value}'"
        )

    now = datetime.now(UTC)
    request.reviewed_by = reviewer_id
    request.reviewed_at = now
    request.review_note = note

    if action == "approve":
        request.status = PrivacyRequestStatus.approved
    elif action == "reject":
        request.status = PrivacyRequestStatus.rejected
    else:
        raise ValueError(f"Invalid action: {action}")

    await db.flush()

    await event_logger.log(
        db,
        matter_id=None,
        actor_id=reviewer_id,
        actor_type=ActorType.user,
        entity_type="privacy_request",
        entity_id=request.id,
        action=f"request_{action}d",
        metadata={"note": note},
    )

    return request


# ---------------------------------------------------------------------------
# Data export — build JSON payload
# ---------------------------------------------------------------------------


async def build_data_export(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Build a complete data export for a user (JSON-serializable).

    Includes: user profile, firm memberships, stakeholder records,
    communications sent, and privacy request history.
    """
    # User profile
    user = await db.execute(select(User).where(User.id == user_id))
    user_obj = user.scalar_one_or_none()
    if not user_obj:
        raise NotFoundError(detail="User not found")

    user_data = {
        "id": str(user_obj.id),
        "email": user_obj.email,
        "full_name": user_obj.full_name,
        "phone": user_obj.phone,
        "avatar_url": user_obj.avatar_url,
        "created_at": user_obj.created_at.isoformat(),
        "updated_at": user_obj.updated_at.isoformat(),
    }

    # Firm memberships
    memberships_q = select(FirmMembership).where(FirmMembership.user_id == user_id)
    memberships = (await db.execute(memberships_q)).scalars().all()
    memberships_data = [
        {
            "id": str(m.id),
            "firm_id": str(m.firm_id),
            "firm_role": m.firm_role.value if hasattr(m.firm_role, "value") else str(m.firm_role),
            "created_at": m.created_at.isoformat(),
        }
        for m in memberships
    ]

    # Stakeholder records
    stakeholders_q = select(Stakeholder).where(Stakeholder.user_id == user_id)
    stakeholders = (await db.execute(stakeholders_q)).scalars().all()
    stakeholders_data = [
        {
            "id": str(s.id),
            "matter_id": str(s.matter_id),
            "email": s.email,
            "full_name": s.full_name,
            "role": s.role.value if hasattr(s.role, "value") else str(s.role),
            "relationship": s.relationship_label,
            "invite_status": s.invite_status.value if hasattr(s.invite_status, "value") else str(s.invite_status),
            "permissions": s.permissions,
            "notification_preferences": s.notification_preferences,
            "created_at": s.created_at.isoformat(),
        }
        for s in stakeholders
    ]

    # Communications sent by this user (via stakeholder records)
    stakeholder_ids = [s.id for s in stakeholders]
    comms_data: list[dict[str, Any]] = []
    if stakeholder_ids:
        comms_q = select(Communication).where(
            Communication.sender_id.in_(stakeholder_ids)
        )
        comms = (await db.execute(comms_q)).scalars().all()
        comms_data = [
            {
                "id": str(c.id),
                "matter_id": str(c.matter_id),
                "type": c.type.value if hasattr(c.type, "value") else str(c.type),
                "subject": c.subject,
                "body": c.body,
                "created_at": c.created_at.isoformat(),
            }
            for c in comms
        ]

    # Privacy requests
    pr_q = select(PrivacyRequest).where(PrivacyRequest.user_id == user_id)
    privacy_requests = (await db.execute(pr_q)).scalars().all()
    pr_data = [
        {
            "id": str(p.id),
            "request_type": p.request_type.value,
            "status": p.status.value,
            "reason": p.reason,
            "created_at": p.created_at.isoformat(),
            "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        }
        for p in privacy_requests
    ]

    return {
        "export_date": datetime.now(UTC).isoformat(),
        "user": user_data,
        "firm_memberships": memberships_data,
        "stakeholder_records": stakeholders_data,
        "communications_sent": comms_data,
        "privacy_requests": pr_data,
    }


# ---------------------------------------------------------------------------
# Data deletion — anonymize PII, retain structural data
# ---------------------------------------------------------------------------


async def process_deletion(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
) -> dict[str, Any]:
    """Process a data deletion request.

    Anonymizes PII in stakeholder records while retaining structural data
    for audit integrity:
    - Stakeholder: name → "[Deleted User]", email → anonymized, phone → null
    - User record: email/name/phone anonymized
    - Communications: does NOT delete message content (audit trail)
    - Events: retained as-is (immutable audit log)

    Returns a summary of what was anonymized.
    """
    result = await db.execute(
        select(PrivacyRequest).where(PrivacyRequest.id == request_id)
    )
    request = result.scalar_one_or_none()
    if not request:
        raise NotFoundError(detail="Privacy request not found")

    if request.status != PrivacyRequestStatus.approved:
        raise PermissionDeniedError(
            detail="Request must be approved before processing"
        )

    request.status = PrivacyRequestStatus.processing
    await db.flush()

    user_id = request.user_id
    summary: dict[str, Any] = {
        "user_anonymized": False,
        "stakeholder_records_anonymized": 0,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Anonymize stakeholder records
    stakeholders_q = select(Stakeholder).where(Stakeholder.user_id == user_id)
    stakeholders = (await db.execute(stakeholders_q)).scalars().all()

    for s in stakeholders:
        s.full_name = ANONYMIZED_NAME
        s.email = f"deleted-{s.id}@anonymized.invalid"
        s.invite_token = None
        s.notification_preferences = {}
        summary["stakeholder_records_anonymized"] += 1

    # Anonymize user record
    user_q = select(User).where(User.id == user_id)
    user_obj = (await db.execute(user_q)).scalar_one_or_none()
    if user_obj:
        user_obj.full_name = ANONYMIZED_NAME
        user_obj.email = f"deleted-{user_obj.id}@anonymized.invalid"
        user_obj.phone = ANONYMIZED_PHONE
        user_obj.avatar_url = None
        summary["user_anonymized"] = True

    # Mark request as completed
    now = datetime.now(UTC)
    request.status = PrivacyRequestStatus.completed
    request.completed_at = now
    request.deletion_summary = summary

    await db.flush()

    await event_logger.log(
        db,
        matter_id=None,
        actor_id=None,
        actor_type=ActorType.system,
        entity_type="privacy_request",
        entity_id=request.id,
        action="deletion_completed",
        metadata=summary,
    )

    logger.info(
        "privacy_deletion_completed",
        extra={
            "request_id": str(request_id),
            "user_id": str(user_id),
            "stakeholders_anonymized": summary["stakeholder_records_anonymized"],
        },
    )

    return summary
