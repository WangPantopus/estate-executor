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


# ---------------------------------------------------------------------------
# Document AI classification (stub)
# ---------------------------------------------------------------------------


@celery_app.task(name="app.workers.tasks.classify_document", bind=True, max_retries=3)
def classify_document(self, document_id: str, matter_id: str):
    """AI classification of an uploaded document.

    Stub implementation — in production this would call the AI service
    to classify the document type and extract structured data.
    """
    try:
        logger.info(
            "classify_document_stub",
            extra={
                "document_id": document_id,
                "matter_id": matter_id,
                "status": "stub_completed",
            },
        )
        return {
            "document_id": document_id,
            "status": "classified",
            "doc_type": None,
            "confidence": None,
        }
    except Exception as exc:
        logger.exception("classify_document failed")
        raise self.retry(exc=exc, countdown=30)


# ---------------------------------------------------------------------------
# Bulk ZIP generation
# ---------------------------------------------------------------------------


@celery_app.task(name="app.workers.tasks.generate_bulk_zip", bind=True, max_retries=2)
def generate_bulk_zip(self, job_id: str, matter_id: str, document_ids: list[str]):
    """Generate a ZIP file containing multiple documents for bulk download.

    Downloads each document from S3, compresses into a ZIP, uploads the ZIP
    back to S3, and returns a presigned download URL.

    Stub implementation — logs the action and returns a placeholder.
    """
    try:
        logger.info(
            "generate_bulk_zip_stub",
            extra={
                "job_id": job_id,
                "matter_id": matter_id,
                "document_count": len(document_ids),
            },
        )
        # In production: download files from S3, create ZIP, upload ZIP,
        # generate presigned URL for the ZIP
        return {
            "job_id": job_id,
            "status": "completed",
            "download_url": None,  # Would be a presigned URL to the ZIP
        }
    except Exception as exc:
        logger.exception("generate_bulk_zip failed")
        raise self.retry(exc=exc, countdown=60)
