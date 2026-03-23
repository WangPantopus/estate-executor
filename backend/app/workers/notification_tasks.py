"""Notification tasks — email dispatch via Resend (prod) or Mailpit (dev).

Uses Jinja2 templates from app/templates/emails/ for premium HTML emails.
All sends are logged to email_logs table (body excluded for PII).
"""

from __future__ import annotations

import asyncio
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Core email sender
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.notification_tasks.send_email",
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=900,
)
def send_email(
    self,
    *,
    to: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
    template_name: str | None = None,
):
    """Send an email via the email service (Resend in prod, Mailpit in dev).

    Retries on transient failures with exponential backoff.
    Logs every send attempt to the email_logs table.
    """
    from app.services.email_service import log_email_sync
    from app.services.email_service import send_email as _send

    try:
        result = _send(
            to=to,
            subject=subject,
            html=html_body,
            text_fallback=text_body,
            template_name=template_name,
        )
        log_email_sync(
            to=to,
            subject=subject,
            template_name=template_name,
            status="sent",
            resend_id=result.get("resend_id"),
        )
        return {"status": "sent", "to": to, "subject": subject}

    except Exception as exc:
        logger.exception("send_email failed", extra={"to": to, "subject": subject})
        log_email_sync(
            to=to,
            subject=subject,
            template_name=template_name,
            status="failed",
            error=str(exc)[:500],
        )
        raise self.retry(exc=exc) from exc


# ---------------------------------------------------------------------------
# Templated email sender (preferred entry point)
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.notification_tasks.send_templated_email",
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=900,
)
def send_templated_email(self, *, to: str, subject: str, template_name: str, context: dict):
    """Render a Jinja2 template and send the email.

    This is the preferred entry point for all notification tasks.
    """
    from app.services.email_service import send_templated_email as _send_templated

    try:
        _send_templated(
            to=to,
            subject=subject,
            template_name=template_name,
            context=context,
        )
        return {"status": "sent", "to": to, "subject": subject}

    except Exception as exc:
        logger.exception(
            "send_templated_email failed",
            extra={"to": to, "subject": subject, "template": template_name},
        )
        raise self.retry(exc=exc) from exc


# ---------------------------------------------------------------------------
# Stakeholder invitation
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.notification_tasks.send_stakeholder_invitation",
    bind=True,
    max_retries=3,
    retry_backoff=True,
)
def send_stakeholder_invitation(self, stakeholder_id: str):
    """Send invitation email to a new stakeholder."""
    try:

        async def _fetch():
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            from app.core.config import settings
            from app.core.database import async_session_factory
            from app.models.matters import Matter
            from app.models.stakeholders import Stakeholder

            async with async_session_factory() as session:
                result = await session.execute(
                    select(Stakeholder)
                    .options(selectinload(Stakeholder.matter).selectinload(Matter.firm))
                    .where(Stakeholder.id == stakeholder_id)
                )
                stakeholder = result.scalar_one_or_none()
                if stakeholder is None:
                    return None

                matter = stakeholder.matter
                firm = matter.firm if matter else None

                # Find who invited (the matter admin who most recently created this stakeholder)
                inviter_name = firm.name if firm else "Estate Executor"

                role_labels = {
                    "matter_admin": "Matter Administrator",
                    "professional": "Professional Advisor",
                    "executor_trustee": "Executor / Trustee",
                    "beneficiary": "Beneficiary",
                    "read_only": "Observer",
                }

                invite_url = f"{settings.frontend_url}/invite/{stakeholder.invite_token}"

                return {
                    "to": stakeholder.email,
                    "recipient_name": stakeholder.full_name,
                    "inviter_name": inviter_name,
                    "decedent_name": matter.decedent_name if matter else "Unknown",
                    "role_label": role_labels.get(
                        stakeholder.role.value
                        if hasattr(stakeholder.role, "value")
                        else stakeholder.role,
                        "Participant",
                    ),
                    "invite_url": invite_url,
                    "firm_name": firm.name if firm else None,
                    "matter_id": str(matter.id) if matter else None,
                }

        info = _run_async(_fetch())
        if info is None:
            return {"status": "skipped", "reason": "stakeholder_not_found"}

        decedent = info["decedent_name"]
        send_templated_email.delay(
            to=info["to"],
            subject=f"You've been invited to the Estate of {decedent}",
            template_name="stakeholder_invitation.html",
            context=info,
        )

        logger.info("stakeholder_invitation_queued", extra={"stakeholder_id": stakeholder_id})
        return {"status": "queued", "stakeholder_id": stakeholder_id}

    except Exception as exc:
        logger.exception("send_stakeholder_invitation failed")
        raise self.retry(exc=exc) from exc


# ---------------------------------------------------------------------------
# Task assignment notification
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.notification_tasks.send_task_assignment_notification",
    bind=True,
    max_retries=3,
    retry_backoff=True,
)
def send_task_assignment_notification(self, task_id: str, assignee_stakeholder_id: str):
    """Notify a stakeholder that a task has been assigned to them."""
    try:

        async def _fetch():
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            from app.core.config import settings
            from app.core.database import async_session_factory
            from app.models.matters import Matter
            from app.models.stakeholders import Stakeholder
            from app.models.tasks import Task

            async with async_session_factory() as session:
                task_result = await session.execute(
                    select(Task)
                    .options(selectinload(Task.matter).selectinload(Matter.firm))
                    .where(Task.id == task_id)
                )
                task = task_result.scalar_one_or_none()

                stakeholder_result = await session.execute(
                    select(Stakeholder).where(Stakeholder.id == assignee_stakeholder_id)
                )
                stakeholder = stakeholder_result.scalar_one_or_none()

                if task is None or stakeholder is None:
                    return None

                matter = task.matter
                firm = matter.firm if matter else None
                str(firm.id) if firm else ""
                matter_id = str(matter.id) if matter else ""

                phase_labels = {
                    "immediate": "Immediate",
                    "asset_inventory": "Asset Inventory",
                    "notification": "Notification",
                    "probate_filing": "Probate Filing",
                    "tax": "Tax",
                    "transfer_distribution": "Transfer & Distribution",
                    "family_communication": "Family Communication",
                    "closing": "Closing",
                    "custom": "Custom",
                }

                priority_labels = {
                    "critical": "Critical",
                    "normal": "Normal",
                    "informational": "Informational",
                }

                phase_val = task.phase.value if hasattr(task.phase, "value") else task.phase
                priority_val = (
                    task.priority.value if hasattr(task.priority, "value") else task.priority
                )

                return {
                    "to": stakeholder.email,
                    "recipient_name": stakeholder.full_name,
                    "task_title": task.title,
                    "task_description": task.description or "",
                    "due_date": str(task.due_date) if task.due_date else None,
                    "phase": phase_labels.get(phase_val, phase_val),
                    "priority": priority_labels.get(priority_val, priority_val),
                    "decedent_name": matter.decedent_name if matter else "Unknown",
                    "firm_name": firm.name if firm else None,
                    "task_url": (
                        f"{settings.frontend_url}/matters/{matter_id}/tasks?task={task_id}"
                    ),
                }

        info = _run_async(_fetch())
        if info is None:
            return {"status": "skipped", "reason": "task_or_stakeholder_not_found"}

        send_templated_email.delay(
            to=info["to"],
            subject=f"New task assigned: {info['task_title']}",
            template_name="task_assigned.html",
            context=info,
        )

        logger.info(
            "task_assignment_notification_queued",
            extra={"task_id": task_id, "assignee": assignee_stakeholder_id},
        )
        return {"status": "queued", "task_id": task_id}

    except Exception as exc:
        logger.exception("send_task_assignment_notification failed")
        raise self.retry(exc=exc) from exc


# ---------------------------------------------------------------------------
# Task overdue notification
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.notification_tasks.send_task_overdue_notification",
    bind=True,
    max_retries=3,
    retry_backoff=True,
)
def send_task_overdue_notification(
    self, *, task_id: str, to: str, recipient_name: str, task_title: str,
    due_date: str, status: str, assigned_to_name: str | None = None,
    decedent_name: str = "Unknown", firm_name: str | None = None,
    matter_id: str = "",
):
    """Send overdue task notification using the premium template."""
    from app.core.config import settings

    try:
        task_url = f"{settings.frontend_url}/matters/{matter_id}/tasks?task={task_id}"

        send_templated_email.delay(
            to=to,
            subject=f"Overdue: {task_title} was due {due_date}",
            template_name="task_overdue.html",
            context={
                "recipient_name": recipient_name,
                "task_title": task_title,
                "due_date": due_date,
                "status": status,
                "assigned_to_name": assigned_to_name,
                "decedent_name": decedent_name,
                "firm_name": firm_name,
                "task_url": task_url,
            },
        )
        return {"status": "queued", "to": to}

    except Exception as exc:
        logger.exception("send_task_overdue_notification failed")
        raise self.retry(exc=exc) from exc


# ---------------------------------------------------------------------------
# Deadline reminder
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.notification_tasks.send_deadline_reminder",
    bind=True,
    max_retries=3,
    retry_backoff=True,
)
def send_deadline_reminder(self, deadline_id: str):
    """Send a reminder email for an approaching deadline."""
    try:

        async def _fetch():
            from datetime import date

            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            from app.core.config import settings
            from app.core.database import async_session_factory
            from app.models.deadlines import Deadline
            from app.models.matters import Matter

            async with async_session_factory() as session:
                result = await session.execute(
                    select(Deadline)
                    .options(
                        selectinload(Deadline.assignee),
                        selectinload(Deadline.task),
                        selectinload(Deadline.matter).selectinload(Matter.firm),
                    )
                    .where(Deadline.id == deadline_id)
                )
                deadline = result.scalar_one_or_none()
                if deadline is None or deadline.assignee is None:
                    return None

                matter = deadline.matter
                firm = matter.firm if matter else None
                days_remaining = (deadline.due_date - date.today()).days
                matter_id = str(matter.id) if matter else ""

                return {
                    "to": deadline.assignee.email,
                    "recipient_name": deadline.assignee.full_name,
                    "deadline_title": deadline.title,
                    "deadline_description": deadline.description or "",
                    "due_date": str(deadline.due_date),
                    "days_remaining": max(days_remaining, 0),
                    "linked_task": deadline.task.title if deadline.task else None,
                    "decedent_name": matter.decedent_name if matter else "Unknown",
                    "firm_name": firm.name if firm else None,
                    "calendar_url": (
                        f"{settings.frontend_url}/matters/{matter_id}/deadlines"
                    ),
                }

        info = _run_async(_fetch())
        if info is None:
            return {"status": "skipped", "reason": "deadline_or_assignee_not_found"}

        send_templated_email.delay(
            to=info["to"],
            subject=f"Deadline approaching: {info['deadline_title']} — due {info['due_date']}",
            template_name="deadline_reminder.html",
            context=info,
        )

        logger.info("deadline_reminder_queued", extra={"deadline_id": deadline_id})
        return {"status": "queued", "deadline_id": deadline_id}

    except Exception as exc:
        logger.exception("send_deadline_reminder failed")
        raise self.retry(exc=exc) from exc


# ---------------------------------------------------------------------------
# Deadline missed notification
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.notification_tasks.send_deadline_missed_notification",
    bind=True,
    max_retries=3,
    retry_backoff=True,
)
def send_deadline_missed_notification(self, deadline_id: str):
    """Send an urgent notification when a deadline has been missed."""
    try:

        async def _fetch():
            from datetime import date

            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            from app.core.config import settings
            from app.core.database import async_session_factory
            from app.models.deadlines import Deadline
            from app.models.enums import StakeholderRole
            from app.models.matters import Matter
            from app.models.stakeholders import Stakeholder

            async with async_session_factory() as session:
                result = await session.execute(
                    select(Deadline)
                    .options(
                        selectinload(Deadline.assignee),
                        selectinload(Deadline.task),
                        selectinload(Deadline.matter).selectinload(Matter.firm),
                    )
                    .where(Deadline.id == deadline_id)
                )
                deadline = result.scalar_one_or_none()
                if deadline is None:
                    return None

                matter = deadline.matter
                firm = matter.firm if matter else None
                days_overdue = (date.today() - deadline.due_date).days
                matter_id = str(matter.id) if matter else ""

                # Notify assignee + all matter admins
                recipients = []
                if deadline.assignee:
                    recipients.append({
                        "to": deadline.assignee.email,
                        "recipient_name": deadline.assignee.full_name,
                    })

                admin_result = await session.execute(
                    select(Stakeholder).where(
                        Stakeholder.matter_id == deadline.matter_id,
                        Stakeholder.role == StakeholderRole.matter_admin,
                    )
                )
                for admin in admin_result.scalars().all():
                    if not any(r["to"] == admin.email for r in recipients):
                        recipients.append({
                            "to": admin.email,
                            "recipient_name": admin.full_name,
                        })

                return {
                    "recipients": recipients,
                    "deadline_title": deadline.title,
                    "deadline_description": deadline.description or "",
                    "due_date": str(deadline.due_date),
                    "days_overdue": days_overdue,
                    "linked_task": deadline.task.title if deadline.task else None,
                    "decedent_name": matter.decedent_name if matter else "Unknown",
                    "firm_name": firm.name if firm else None,
                    "calendar_url": (
                        f"{settings.frontend_url}/matters/{matter_id}/deadlines"
                    ),
                }

        info = _run_async(_fetch())
        if info is None:
            return {"status": "skipped", "reason": "deadline_not_found"}

        for recipient in info["recipients"]:
            ctx = {k: v for k, v in info.items() if k != "recipients"}
            ctx["recipient_name"] = recipient["recipient_name"]

            send_templated_email.delay(
                to=recipient["to"],
                subject=f"\u26a0\ufe0f MISSED: {info['deadline_title']} was due {info['due_date']}",
                template_name="deadline_missed.html",
                context=ctx,
            )

        logger.info(
            "deadline_missed_notification_queued",
            extra={"deadline_id": deadline_id, "recipient_count": len(info["recipients"])},
        )
        return {"status": "queued", "deadline_id": deadline_id}

    except Exception as exc:
        logger.exception("send_deadline_missed_notification failed")
        raise self.retry(exc=exc) from exc


# ---------------------------------------------------------------------------
# Milestone notification
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.notification_tasks.send_milestone_notification",
    bind=True,
    max_retries=3,
    retry_backoff=True,
)
def send_milestone_notification(
    self, matter_id: str, milestone_type: str, stakeholder_ids: list[str],
    milestone_description: str | None = None, progress_summary: str | None = None,
):
    """Notify stakeholders about a milestone in the matter."""
    try:

        async def _fetch():
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            from app.core.config import settings
            from app.core.database import async_session_factory
            from app.models.matters import Matter
            from app.models.stakeholders import Stakeholder

            async with async_session_factory() as session:
                matter_result = await session.execute(
                    select(Matter)
                    .options(selectinload(Matter.firm))
                    .where(Matter.id == matter_id)
                )
                matter = matter_result.scalar_one_or_none()

                result = await session.execute(
                    select(Stakeholder).where(Stakeholder.id.in_(stakeholder_ids))
                )
                stakeholders = result.scalars().all()

                firm = matter.firm if matter else None

                return {
                    "recipients": [
                        {"to": s.email, "recipient_name": s.full_name} for s in stakeholders
                    ],
                    "decedent_name": matter.decedent_name if matter else "Unknown",
                    "firm_name": firm.name if firm else None,
                    "matter_url": f"{settings.frontend_url}/matters/{matter_id}",
                }

        info = _run_async(_fetch())

        for recipient in info["recipients"]:
            send_templated_email.delay(
                to=recipient["to"],
                subject=(
                    f"Estate of {info['decedent_name']} — milestone reached: {milestone_type}"
                ),
                template_name="milestone_notification.html",
                context={
                    "recipient_name": recipient["recipient_name"],
                    "decedent_name": info["decedent_name"],
                    "milestone": milestone_type,
                    "milestone_description": milestone_description or "",
                    "progress_summary": progress_summary or "",
                    "firm_name": info["firm_name"],
                    "matter_url": info["matter_url"],
                },
            )

        logger.info(
            "milestone_notification_queued",
            extra={
                "matter_id": matter_id,
                "milestone_type": milestone_type,
                "recipient_count": len(info["recipients"]),
            },
        )
        return {"status": "queued", "recipient_count": len(info["recipients"])}

    except Exception as exc:
        logger.exception("send_milestone_notification failed")
        raise self.retry(exc=exc) from exc


# ---------------------------------------------------------------------------
# Distribution notice
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.notification_tasks.send_distribution_notice",
    bind=True,
    max_retries=3,
    retry_backoff=True,
)
def send_distribution_notice(
    self, *, matter_id: str, communication_id: str,
    to: str, recipient_name: str, decedent_name: str,
    distribution_details: str, amount: str | None = None,
    firm_name: str | None = None,
):
    """Send distribution notice email to a beneficiary."""
    from app.core.config import settings

    try:
        acknowledge_url = (
            f"{settings.frontend_url}/matters/{matter_id}/communications"
            f"?acknowledge={communication_id}"
        )

        send_templated_email.delay(
            to=to,
            subject=f"Distribution Notice — Estate of {decedent_name}",
            template_name="distribution_notice.html",
            context={
                "recipient_name": recipient_name,
                "decedent_name": decedent_name,
                "distribution_details": distribution_details,
                "amount": amount,
                "firm_name": firm_name,
                "acknowledge_url": acknowledge_url,
            },
        )
        return {"status": "queued", "to": to}

    except Exception as exc:
        logger.exception("send_distribution_notice failed")
        raise self.retry(exc=exc) from exc


# ---------------------------------------------------------------------------
# Document request
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.notification_tasks.send_document_request",
    bind=True,
    max_retries=3,
    retry_backoff=True,
)
def send_document_request(
    self, *, matter_id: str, to: str, recipient_name: str,
    requester_name: str, doc_type: str, reason: str | None = None,
    decedent_name: str = "Unknown", firm_name: str | None = None,
):
    """Send document request email to a stakeholder."""
    from app.core.config import settings

    try:
        upload_url = f"{settings.frontend_url}/matters/{matter_id}/documents?upload=true"

        send_templated_email.delay(
            to=to,
            subject=f"Document requested: {doc_type}",
            template_name="document_request.html",
            context={
                "recipient_name": recipient_name,
                "requester_name": requester_name,
                "doc_type": doc_type,
                "reason": reason,
                "decedent_name": decedent_name,
                "firm_name": firm_name,
                "upload_url": upload_url,
            },
        )
        return {"status": "queued", "to": to}

    except Exception as exc:
        logger.exception("send_document_request failed")
        raise self.retry(exc=exc) from exc
