"""Milestone detection and auto-notification service.

Defines milestones based on task phase completion and triggers notifications
when all tasks in a milestone group are complete.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from app.core.events import event_logger
from app.models.communications import Communication
from app.models.enums import (
    ActorType,
    CommunicationType,
    CommunicationVisibility,
    StakeholderRole,
    TaskPhase,
    TaskStatus,
)
from app.models.stakeholders import Stakeholder
from app.models.tasks import Task

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

# Terminal task states — tasks that are "done" (don't block milestone)
_TERMINAL_STATES = {TaskStatus.complete, TaskStatus.waived, TaskStatus.cancelled}

# ---------------------------------------------------------------------------
# Milestone definitions
# ---------------------------------------------------------------------------

MILESTONE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "key": "immediate_tasks_complete",
        "title": "All Immediate Tasks Complete",
        "description": "All initial and urgent tasks have been completed.",
        "phase": TaskPhase.immediate,
    },
    {
        "key": "inventory_complete",
        "title": "Inventory Complete",
        "description": "All assets have been inventoried and documented.",
        "phase": TaskPhase.asset_inventory,
    },
    {
        "key": "probate_filed",
        "title": "Probate Filed",
        "description": "Probate petition and related filings have been completed.",
        "phase": TaskPhase.probate_filing,
    },
    {
        "key": "tax_returns_filed",
        "title": "All Tax Returns Filed",
        "description": "All required tax returns have been prepared and filed.",
        "phase": TaskPhase.tax,
    },
    {
        "key": "distribution_approved",
        "title": "Distribution Approved",
        "description": "Asset distribution to beneficiaries has been approved.",
        "phase": TaskPhase.transfer_distribution,
    },
]

# Map phase → milestone key for quick lookup
_PHASE_TO_MILESTONE: dict[TaskPhase, str] = {m["phase"]: m["key"] for m in MILESTONE_DEFINITIONS}


def get_milestone_definition(key: str) -> dict[str, Any] | None:
    """Look up a milestone definition by key."""
    for m in MILESTONE_DEFINITIONS:
        if m["key"] == key:
            return m
    return None


# ---------------------------------------------------------------------------
# Detection: check if a phase milestone was just achieved
# ---------------------------------------------------------------------------


async def check_phase_milestone(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    phase: TaskPhase,
) -> bool:
    """Check if ALL tasks in the given phase are in a terminal state.

    Returns True if the milestone was just achieved (all tasks done, and
    no existing milestone_notification communication for this milestone).
    Returns False if no tasks exist in this phase, or some are still active.
    """
    milestone_key = _PHASE_TO_MILESTONE.get(phase)
    if milestone_key is None:
        return False

    # Count total tasks and completed tasks in the phase
    total_q = (
        select(func.count())
        .select_from(Task)
        .where(Task.matter_id == matter_id, Task.phase == phase)
    )
    total = (await db.execute(total_q)).scalar_one()

    if total == 0:
        return False  # No tasks in this phase — no milestone to detect

    terminal_q = (
        select(func.count())
        .select_from(Task)
        .where(
            Task.matter_id == matter_id,
            Task.phase == phase,
            Task.status.in_(list(_TERMINAL_STATES)),
        )
    )
    terminal_count = (await db.execute(terminal_q)).scalar_one()

    if terminal_count < total:
        return False  # Not all tasks are done yet

    # Check if we already fired this milestone notification
    existing_q = (
        select(func.count())
        .select_from(Communication)
        .where(
            Communication.matter_id == matter_id,
            Communication.type == CommunicationType.milestone_notification,
            Communication.subject == _get_milestone_subject(milestone_key),
        )
    )
    already_fired = (await db.execute(existing_q)).scalar_one()

    return already_fired == 0


def _get_milestone_subject(milestone_key: str) -> str:
    """Build the communication subject for a milestone."""
    defn = get_milestone_definition(milestone_key)
    if defn:
        return f"Milestone: {defn['title']}"
    return f"Milestone: {milestone_key}"


# ---------------------------------------------------------------------------
# Fire milestone notification
# ---------------------------------------------------------------------------


async def fire_milestone_notification(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    milestone_key: str,
    actor_id: uuid.UUID | None = None,
) -> Communication | None:
    """Create a milestone Communication and dispatch email notifications.

    Checks matter.settings['milestone_notifications'] to see if auto-notify
    is enabled for this milestone. If disabled, still creates the record
    but skips email dispatch.

    Returns the Communication record, or None if milestone not found.
    """
    from app.models.matters import Matter

    defn = get_milestone_definition(milestone_key)
    if defn is None:
        logger.warning("Unknown milestone key: %s", milestone_key)
        return None

    # Fetch matter to check settings
    matter_result = await db.execute(select(Matter).where(Matter.id == matter_id))
    matter = matter_result.scalar_one_or_none()
    if matter is None:
        return None

    subject = _get_milestone_subject(milestone_key)

    # Resolve sender_id: use actor_id if provided, otherwise find a matter_admin
    sender_id = actor_id
    if sender_id is None:
        admin_result = await db.execute(
            select(Stakeholder.id)
            .where(
                Stakeholder.matter_id == matter_id,
                Stakeholder.role == StakeholderRole.matter_admin,
            )
            .limit(1)
        )
        admin_row = admin_result.scalar_one_or_none()
        if admin_row is None:
            logger.warning(
                "No matter_admin found for milestone sender",
                extra={"matter_id": str(matter_id)},
            )
            return None
        sender_id = admin_row

    # Create the milestone communication record
    comm = Communication(
        matter_id=matter_id,
        sender_id=sender_id,
        type=CommunicationType.milestone_notification,
        subject=subject,
        body=defn["description"],
        visibility=CommunicationVisibility.all_stakeholders,
        visible_to=None,
        acknowledged_by=[],
    )
    db.add(comm)
    await db.flush()

    # Log event
    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=actor_id,
        actor_type=ActorType.system,
        entity_type="milestone",
        entity_id=comm.id,
        action="milestone_achieved",
        metadata={
            "milestone_key": milestone_key,
            "milestone_title": defn["title"],
            "phase": defn["phase"].value if hasattr(defn["phase"], "value") else defn["phase"],
        },
    )

    # Check if auto-notifications are enabled for this milestone
    milestone_settings = (matter.settings or {}).get("milestone_notifications", {})
    auto_notify = milestone_settings.get(milestone_key, True)  # Default: enabled

    if auto_notify:
        # Get all beneficiaries + executors for notification
        stakeholder_result = await db.execute(
            select(Stakeholder).where(
                Stakeholder.matter_id == matter_id,
                Stakeholder.role.in_(
                    [
                        StakeholderRole.beneficiary,
                        StakeholderRole.executor_trustee,
                    ]
                ),
            )
        )
        recipients = list(stakeholder_result.scalars().all())

        if recipients:
            try:
                from app.workers.notification_tasks import send_milestone_notification

                send_milestone_notification.delay(
                    matter_id=str(matter_id),
                    milestone_type=defn["title"],
                    stakeholder_ids=[str(s.id) for s in recipients],
                    milestone_description=defn["description"],
                )
            except Exception:
                logger.warning(
                    "Failed to enqueue milestone notification",
                    exc_info=True,
                    extra={"milestone_key": milestone_key, "matter_id": str(matter_id)},
                )
    else:
        logger.info(
            "milestone_notification_disabled",
            extra={"milestone_key": milestone_key, "matter_id": str(matter_id)},
        )

    return comm


# ---------------------------------------------------------------------------
# Post-completion hook: detect milestones after task completion
# ---------------------------------------------------------------------------


async def detect_milestones_after_completion(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    completed_task_phase: TaskPhase,
    actor_id: uuid.UUID | None = None,
) -> list[str]:
    """Check if completing a task in the given phase triggers a milestone.

    Called by task_service.complete_task() after a task is marked complete.
    Returns list of milestone keys that were fired.
    """
    fired: list[str] = []

    milestone_key = _PHASE_TO_MILESTONE.get(completed_task_phase)
    if milestone_key is None:
        return fired

    achieved = await check_phase_milestone(db, matter_id=matter_id, phase=completed_task_phase)

    if achieved:
        comm = await fire_milestone_notification(
            db,
            matter_id=matter_id,
            milestone_key=milestone_key,
            actor_id=actor_id,
        )
        if comm:
            fired.append(milestone_key)
            logger.info(
                "milestone_auto_detected",
                extra={
                    "milestone_key": milestone_key,
                    "matter_id": str(matter_id),
                    "phase": completed_task_phase.value,
                },
            )

    return fired


# ---------------------------------------------------------------------------
# Get milestone status for a matter (dashboard display)
# ---------------------------------------------------------------------------


async def get_milestone_status(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Get the status of all defined milestones for a matter.

    Returns a list of milestone statuses with completion info.
    """
    from app.models.matters import Matter

    # Get matter settings for notification preferences
    matter_result = await db.execute(select(Matter.settings).where(Matter.id == matter_id))
    settings_row = matter_result.scalar_one_or_none()
    milestone_settings = (settings_row or {}).get("milestone_notifications", {})

    # Count tasks per phase (total and terminal)
    phase_counts_q = (
        select(
            Task.phase,
            func.count().label("total"),
            func.count().filter(Task.status.in_(list(_TERMINAL_STATES))).label("completed"),
        )
        .where(Task.matter_id == matter_id)
        .group_by(Task.phase)
    )
    phase_counts = {
        row[0]: {"total": row[1], "completed": row[2]}
        for row in (await db.execute(phase_counts_q)).all()
    }

    # Get existing milestone communications
    milestone_comms_q = (
        select(Communication.subject, Communication.created_at)
        .where(
            Communication.matter_id == matter_id,
            Communication.type == CommunicationType.milestone_notification,
        )
        .order_by(Communication.created_at)
    )
    milestone_comms = {row[0]: row[1] for row in (await db.execute(milestone_comms_q)).all()}

    result = []
    for defn in MILESTONE_DEFINITIONS:
        phase = defn["phase"]
        counts = phase_counts.get(phase, {"total": 0, "completed": 0})
        subject = _get_milestone_subject(defn["key"])
        achieved_at = milestone_comms.get(subject)

        is_complete = counts["total"] > 0 and counts["completed"] == counts["total"]

        result.append(
            {
                "key": defn["key"],
                "title": defn["title"],
                "description": defn["description"],
                "phase": phase.value if hasattr(phase, "value") else phase,
                "total_tasks": counts["total"],
                "completed_tasks": counts["completed"],
                "is_complete": is_complete,
                "achieved_at": achieved_at.isoformat() if achieved_at else None,
                "auto_notify": milestone_settings.get(defn["key"], True),
            }
        )

    return result


# ---------------------------------------------------------------------------
# Update milestone notification settings
# ---------------------------------------------------------------------------


async def update_milestone_settings(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    milestone_key: str,
    enabled: bool,
    current_user: CurrentUser,
) -> dict[str, bool]:
    """Enable or disable auto-notifications for a specific milestone.

    Stores preferences in matter.settings['milestone_notifications'].
    """
    from app.models.matters import Matter

    matter_result = await db.execute(select(Matter).where(Matter.id == matter_id))
    matter = matter_result.scalar_one_or_none()
    if matter is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(detail="Matter not found")

    # Validate milestone key
    if get_milestone_definition(milestone_key) is None:
        from app.core.exceptions import BadRequestError

        raise BadRequestError(detail=f"Unknown milestone: {milestone_key}")

    # Update settings
    settings = dict(matter.settings) if matter.settings else {}
    notifications = dict(settings.get("milestone_notifications", {}))
    notifications[milestone_key] = enabled
    settings["milestone_notifications"] = notifications
    matter.settings = settings
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="matter",
        entity_id=matter_id,
        action="milestone_settings_updated",
        changes={
            "milestone_notifications": {
                "old": {milestone_key: not enabled},
                "new": {milestone_key: enabled},
            }
        },
    )

    return notifications
