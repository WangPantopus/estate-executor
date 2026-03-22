"""Celery tasks for background processing."""

from __future__ import annotations

import asyncio
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from synchronous Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.tasks.check_deadlines", bind=True, max_retries=3)
def check_deadlines(self):
    """Hourly Celery beat task: check for overdue and reminder-due deadlines.

    For each active matter:
    - Marks overdue 'upcoming' deadlines as 'missed' and logs an alert event
    - Sends reminders for deadlines matching their reminder_config.days_before
    - Idempotent: won't send duplicate reminders for the same day
    """
    try:
        stats = _run_async(_check_deadlines_async())
        logger.info(
            "check_deadlines completed",
            extra={"stats": stats},
        )
        return stats
    except Exception as exc:
        logger.exception("check_deadlines failed")
        raise self.retry(exc=exc, countdown=60)


async def _check_deadlines_async() -> dict[str, int]:
    """Async implementation of the deadline check."""
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
