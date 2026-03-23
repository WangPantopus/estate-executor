"""Report generation Celery tasks — async PDF/XLSX generation.

Used for large reports that may take >5 seconds. The generated file
is uploaded to S3 and a presigned download URL is returned.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="app.workers.report_tasks.generate_report_task",
    bind=True,
    max_retries=2,
    retry_backoff=True,
    soft_time_limit=120,
    time_limit=180,
)
def generate_report_task(
    self,
    *,
    job_id: str,
    matter_id: str,
    report_type: str,
    output_format: str = "pdf",
):
    """Generate a report asynchronously, upload to S3, return download URL."""
    try:

        async def _generate():
            from app.core.config import settings
            from app.core.database import async_session_factory
            from app.services import report_service
            from app.services.storage_service import _get_s3_client, generate_download_url

            async with async_session_factory() as session:
                content, filename, content_type = await report_service.generate_report(
                    session,
                    matter_id=matter_id,
                    report_type=report_type,
                    output_format=output_format,
                )

            # Upload to S3
            storage_key = f"firms/reports/{matter_id}/{job_id}/{filename}"
            s3 = _get_s3_client()
            s3.put_object(
                Bucket=settings.aws_s3_bucket,
                Key=storage_key,
                Body=content,
                ContentType=content_type,
            )

            download_url = generate_download_url(storage_key=storage_key)

            return {
                "job_id": job_id,
                "status": "completed",
                "download_url": download_url,
                "filename": filename,
            }

        result = _run_async(_generate())
        logger.info(
            "report_generated",
            extra={
                "job_id": job_id,
                "report_type": report_type,
                "format": output_format,
            },
        )
        return result

    except Exception as exc:
        logger.exception(
            "report_generation_failed",
            extra={"job_id": job_id, "report_type": report_type},
        )
        raise self.retry(exc=exc) from exc
