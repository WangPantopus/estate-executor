"""Deadline and overdue task monitoring — Celery beat periodic tasks."""

from __future__ import annotations

import asyncio
import logging
from datetime import date

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# check_deadlines — runs every hour via Celery beat
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.deadline_tasks.check_deadlines",
    bind=True,
    max_retries=3,
    retry_backoff=True,
)
def check_deadlines(self):
    """Hourly beat task: find overdue and reminder-due deadlines.

    For each active matter:
    - Marks overdue 'upcoming' deadlines as 'missed', sends alert
    - Sends reminders based on reminder_config.days_before
    - Dispatches send_deadline_reminder for each
    - Idempotent: won't send duplicate reminders for the same day
    """
    try:
        stats = _run_async(_check_deadlines_async())
        logger.info("check_deadlines completed", extra={"stats": stats})
        return stats
    except Exception as exc:
        logger.exception("check_deadlines failed")
        raise self.retry(exc=exc)


async def _check_deadlines_async() -> dict[str, int]:
    from app.core.database import async_session_factory
    from app.services import deadline_service

    async with async_session_factory() as session:
        try:
            stats = await deadline_service.check_deadlines(session)
            await session.commit()
            return stats
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# check_overdue_tasks — runs every 6 hours via Celery beat
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.deadline_tasks.check_overdue_tasks",
    bind=True,
    max_retries=3,
    retry_backoff=True,
)
def check_overdue_tasks(self):
    """Periodic task: find tasks past due_date still in not_started or in_progress.

    Sends notifications to the assignee and matter admins.
    """
    try:
        stats = _run_async(_check_overdue_tasks_async())
        logger.info("check_overdue_tasks completed", extra={"stats": stats})
        return stats
    except Exception as exc:
        logger.exception("check_overdue_tasks failed")
        raise self.retry(exc=exc)


async def _check_overdue_tasks_async() -> dict[str, int]:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.core.database import async_session_factory
    from app.models.enums import MatterStatus, StakeholderRole, TaskStatus
    from app.models.matters import Matter
    from app.models.stakeholders import Stakeholder
    from app.models.tasks import Task

    today = date.today()
    stats = {"overdue_tasks_found": 0, "notifications_sent": 0}

    async with async_session_factory() as session:
        try:
            # Get active matters
            active_matters = await session.execute(
                select(Matter.id).where(Matter.status == MatterStatus.active)
            )
            matter_ids = [row[0] for row in active_matters.all()]

            if not matter_ids:
                return stats

            # Find overdue tasks
            overdue_q = select(Task).where(
                Task.matter_id.in_(matter_ids),
                Task.status.in_([TaskStatus.not_started, TaskStatus.in_progress]),
                Task.due_date < today,
                Task.due_date.isnot(None),
            )
            result = await session.execute(overdue_q)
            overdue_tasks = result.scalars().all()

            for task in overdue_tasks:
                stats["overdue_tasks_found"] += 1

                # Notify assignee
                if task.assigned_to is not None:
                    from app.workers.notification_tasks import send_email

                    assignee_result = await session.execute(
                        select(Stakeholder).where(Stakeholder.id == task.assigned_to)
                    )
                    assignee = assignee_result.scalar_one_or_none()
                    if assignee:
                        send_email.delay(
                            to=assignee.email,
                            subject=f"Overdue task: {task.title}",
                            html_body=f"<p>Hello {assignee.full_name},</p>"
                            f"<p>The task <strong>{task.title}</strong> was due on "
                            f"{task.due_date} and is still {task.status.value}.</p>",
                        )
                        stats["notifications_sent"] += 1

                # Notify matter admins
                admin_result = await session.execute(
                    select(Stakeholder).where(
                        Stakeholder.matter_id == task.matter_id,
                        Stakeholder.role == StakeholderRole.matter_admin,
                    )
                )
                admins = admin_result.scalars().all()
                for admin in admins:
                    from app.workers.notification_tasks import send_email

                    send_email.delay(
                        to=admin.email,
                        subject=f"Overdue task alert: {task.title}",
                        html_body=f"<p>Hello {admin.full_name},</p>"
                        f"<p>The task <strong>{task.title}</strong> is overdue "
                        f"(due: {task.due_date}, status: {task.status.value}).</p>",
                    )
                    stats["notifications_sent"] += 1

            await session.commit()
            return stats
        except Exception:
            await session.rollback()
            raise
