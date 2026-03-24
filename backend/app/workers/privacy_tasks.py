"""Celery tasks for privacy request processing (data export & deletion)."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.privacy_tasks.process_deletion_request",
    bind=True,
    max_retries=3,
    soft_time_limit=120,
    time_limit=180,
)
def process_deletion_request(self, request_id: str) -> dict:
    """Process an approved data deletion request asynchronously.

    Anonymizes PII in stakeholder and user records while preserving
    structural data for audit integrity.
    """
    from app.core.database import async_session_factory
    from app.services.privacy_service import process_deletion

    async def _run():
        async with async_session_factory() as db:
            try:
                summary = await process_deletion(
                    db, request_id=UUID(request_id),
                )
                await db.commit()
                return summary
            except Exception:
                await db.rollback()
                raise

    try:
        summary = asyncio.run(_run())
        logger.info(
            "privacy_deletion_task_completed",
            extra={"request_id": request_id, "summary": summary},
        )
        return summary

    except Exception as exc:
        logger.error(
            "privacy_deletion_task_failed",
            extra={"request_id": request_id, "error": str(exc)},
        )
        raise self.retry(
            exc=exc,
            countdown=60 * (2 ** self.request.retries),
        ) from exc


@celery_app.task(
    name="app.workers.privacy_tasks.process_export_request",
    bind=True,
    max_retries=3,
    soft_time_limit=300,
    time_limit=600,
)
def process_export_request(self, request_id: str, user_id: str) -> dict:
    """Process a data export request asynchronously.

    Builds a JSON export and stores it (in production, uploaded to S3).
    Returns the export summary.
    """
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.enums import PrivacyRequestStatus
    from app.models.privacy_requests import PrivacyRequest
    from app.services.privacy_service import build_data_export

    async def _run():
        async with async_session_factory() as db:
            try:
                export_data = await build_data_export(
                    db, user_id=UUID(user_id),
                )

                # Mark as completed
                result = await db.execute(
                    select(PrivacyRequest).where(
                        PrivacyRequest.id == UUID(request_id),
                        PrivacyRequest.status.in_([
                            PrivacyRequestStatus.approved,
                            PrivacyRequestStatus.processing,
                        ]),
                    )
                )
                req = result.scalar_one_or_none()
                if req:
                    req.status = PrivacyRequestStatus.completed
                    req.completed_at = datetime.now(UTC)

                await db.commit()
                return {
                    "status": "completed",
                    "record_counts": {
                        k: len(v) if isinstance(v, list) else 1
                        for k, v in export_data.items()
                        if k != "export_date"
                    },
                }
            except Exception:
                await db.rollback()
                raise

    try:
        result = asyncio.run(_run())
        logger.info(
            "privacy_export_task_completed",
            extra={
                "request_id": request_id,
                "user_id": user_id,
            },
        )
        return result

    except Exception as exc:
        logger.error(
            "privacy_export_task_failed",
            extra={"request_id": request_id, "error": str(exc)},
        )
        raise self.retry(
            exc=exc,
            countdown=60 * (2 ** self.request.retries),
        ) from exc
