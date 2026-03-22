"""Notification tasks — email dispatch via Resend API (stub)."""

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
def send_email(self, *, to: str, subject: str, html_body: str, text_body: str | None = None):
    """Send an email via Resend API.

    Stub: logs the email content. In production, calls the Resend API.
    Retries on transient failures with exponential backoff.
    """
    try:
        logger.info(
            "send_email_stub",
            extra={
                "to": to,
                "subject": subject,
                "html_body_length": len(html_body),
                "has_text_body": text_body is not None,
            },
        )
        # In production:
        # import resend
        # from app.core.config import settings
        # resend.api_key = settings.resend_api_key
        # resend.Emails.send({
        #     "from": settings.email_from,
        #     "to": to,
        #     "subject": subject,
        #     "html": html_body,
        #     "text": text_body,
        # })
        return {"status": "sent", "to": to, "subject": subject}
    except Exception as exc:
        logger.exception("send_email failed", extra={"to": to, "subject": subject})
        raise self.retry(exc=exc)


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

        async def _send():
            from app.core.config import settings
            from app.core.database import async_session_factory
            from app.models.stakeholders import Stakeholder
            from sqlalchemy import select

            async with async_session_factory() as session:
                result = await session.execute(
                    select(Stakeholder).where(Stakeholder.id == stakeholder_id)
                )
                stakeholder = result.scalar_one_or_none()
                if stakeholder is None:
                    logger.warning("stakeholder not found for invitation", extra={"stakeholder_id": stakeholder_id})
                    return None

                invite_url = f"{settings.frontend_url}/invite/{stakeholder.invite_token}"
                return {
                    "to": stakeholder.email,
                    "name": stakeholder.full_name,
                    "invite_url": invite_url,
                }

        info = _run_async(_send())
        if info is None:
            return {"status": "skipped", "reason": "stakeholder_not_found"}

        send_email.delay(
            to=info["to"],
            subject="You've been invited to Estate Executor",
            html_body=f"<p>Hello {info['name']},</p><p>You've been invited. "
            f"<a href='{info['invite_url']}'>Accept invitation</a></p>",
        )

        logger.info("stakeholder_invitation_sent", extra={"stakeholder_id": stakeholder_id})
        return {"status": "sent", "stakeholder_id": stakeholder_id}

    except Exception as exc:
        logger.exception("send_stakeholder_invitation failed")
        raise self.retry(exc=exc)


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

        async def _send():
            from app.core.database import async_session_factory
            from app.models.stakeholders import Stakeholder
            from app.models.tasks import Task
            from sqlalchemy import select

            async with async_session_factory() as session:
                task_result = await session.execute(select(Task).where(Task.id == task_id))
                task = task_result.scalar_one_or_none()
                stakeholder_result = await session.execute(
                    select(Stakeholder).where(Stakeholder.id == assignee_stakeholder_id)
                )
                stakeholder = stakeholder_result.scalar_one_or_none()

                if task is None or stakeholder is None:
                    return None

                return {
                    "to": stakeholder.email,
                    "name": stakeholder.full_name,
                    "task_title": task.title,
                }

        info = _run_async(_send())
        if info is None:
            return {"status": "skipped", "reason": "task_or_stakeholder_not_found"}

        send_email.delay(
            to=info["to"],
            subject=f"Task assigned: {info['task_title']}",
            html_body=f"<p>Hello {info['name']},</p>"
            f"<p>You have been assigned the task: <strong>{info['task_title']}</strong></p>",
        )

        logger.info(
            "task_assignment_notification_sent",
            extra={"task_id": task_id, "assignee": assignee_stakeholder_id},
        )
        return {"status": "sent", "task_id": task_id}

    except Exception as exc:
        logger.exception("send_task_assignment_notification failed")
        raise self.retry(exc=exc)


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

        async def _send():
            from app.core.database import async_session_factory
            from app.models.deadlines import Deadline
            from app.models.stakeholders import Stakeholder
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            async with async_session_factory() as session:
                result = await session.execute(
                    select(Deadline)
                    .options(selectinload(Deadline.assignee))
                    .where(Deadline.id == deadline_id)
                )
                deadline = result.scalar_one_or_none()
                if deadline is None or deadline.assignee is None:
                    return None

                return {
                    "to": deadline.assignee.email,
                    "name": deadline.assignee.full_name,
                    "title": deadline.title,
                    "due_date": str(deadline.due_date),
                }

        info = _run_async(_send())
        if info is None:
            return {"status": "skipped", "reason": "deadline_or_assignee_not_found"}

        send_email.delay(
            to=info["to"],
            subject=f"Deadline reminder: {info['title']}",
            html_body=f"<p>Hello {info['name']},</p>"
            f"<p>Reminder: <strong>{info['title']}</strong> is due on {info['due_date']}.</p>",
        )

        logger.info("deadline_reminder_sent", extra={"deadline_id": deadline_id})
        return {"status": "sent", "deadline_id": deadline_id}

    except Exception as exc:
        logger.exception("send_deadline_reminder failed")
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Milestone notification
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.notification_tasks.send_milestone_notification",
    bind=True,
    max_retries=3,
    retry_backoff=True,
)
def send_milestone_notification(self, matter_id: str, milestone_type: str, stakeholder_ids: list[str]):
    """Notify stakeholders about a milestone in the matter."""
    try:

        async def _send():
            from app.core.database import async_session_factory
            from app.models.stakeholders import Stakeholder
            from sqlalchemy import select

            async with async_session_factory() as session:
                result = await session.execute(
                    select(Stakeholder).where(Stakeholder.id.in_(stakeholder_ids))
                )
                stakeholders = result.scalars().all()
                return [{"to": s.email, "name": s.full_name} for s in stakeholders]

        recipients = _run_async(_send())

        for r in recipients:
            send_email.delay(
                to=r["to"],
                subject=f"Milestone reached: {milestone_type}",
                html_body=f"<p>Hello {r['name']},</p>"
                f"<p>A milestone has been reached: <strong>{milestone_type}</strong>.</p>",
            )

        logger.info(
            "milestone_notification_sent",
            extra={
                "matter_id": matter_id,
                "milestone_type": milestone_type,
                "recipient_count": len(recipients),
            },
        )
        return {"status": "sent", "recipient_count": len(recipients)}

    except Exception as exc:
        logger.exception("send_milestone_notification failed")
        raise self.retry(exc=exc)
