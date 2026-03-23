"""Document processing tasks — bulk download ZIP generation."""

from __future__ import annotations

import asyncio
import io
import logging
import zipfile

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="app.workers.document_tasks.generate_bulk_download",
    bind=True,
    max_retries=2,
    retry_backoff=True,
    soft_time_limit=600,
    time_limit=900,
)
def generate_bulk_download(
    self,
    job_id: str,
    matter_id: str,
    document_ids: list[str],
    requester_stakeholder_id: str,
):
    """Generate a ZIP file containing multiple documents for bulk download.

    1. Fetches document metadata from DB
    2. Downloads each document from S3
    3. Creates a ZIP archive in memory
    4. Uploads the ZIP to S3
    5. Notifies the requester with a presigned download URL
    """
    try:

        async def _generate():
            from sqlalchemy import select

            from app.core.config import settings
            from app.core.database import async_session_factory
            from app.models.documents import Document
            from app.models.stakeholders import Stakeholder
            from app.services.storage_service import (
                _get_s3_client,
                generate_download_url,
            )

            async with async_session_factory() as session:
                # Fetch documents
                result = await session.execute(
                    select(Document).where(
                        Document.id.in_(document_ids),
                        Document.matter_id == matter_id,
                    )
                )
                docs = list(result.scalars().all())

                if not docs:
                    logger.warning(
                        "bulk_download_no_documents",
                        extra={"job_id": job_id, "matter_id": matter_id},
                    )
                    return {"job_id": job_id, "status": "completed", "download_url": None}

                # Download files from S3 and build ZIP
                s3 = _get_s3_client()
                zip_buffer = io.BytesIO()

                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for doc in docs:
                        try:
                            response = s3.get_object(
                                Bucket=settings.aws_s3_bucket,
                                Key=doc.storage_key,
                            )
                            file_data = response["Body"].read()
                            zf.writestr(doc.filename, file_data)
                        except Exception:
                            logger.warning(
                                "bulk_download_file_skipped",
                                extra={
                                    "document_id": str(doc.id),
                                    "storage_key": doc.storage_key,
                                },
                            )

                zip_buffer.seek(0)

                # Upload ZIP to S3
                zip_key = f"firms/bulk-downloads/{matter_id}/{job_id}.zip"
                s3.put_object(
                    Bucket=settings.aws_s3_bucket,
                    Key=zip_key,
                    Body=zip_buffer.getvalue(),
                    ContentType="application/zip",
                )

                # Generate download URL
                download_url = generate_download_url(storage_key=zip_key)

                # Notify requester
                requester_result = await session.execute(
                    select(Stakeholder).where(Stakeholder.id == requester_stakeholder_id)
                )
                requester = requester_result.scalar_one_or_none()
                if requester:
                    from app.workers.notification_tasks import send_email

                    send_email.delay(
                        to=requester.email,
                        subject="Your document download is ready",
                        html_body=f"<p>Hello {requester.full_name},</p>"
                        f"<p>Your bulk download ({len(docs)} documents) is ready. "
                        f"<a href='{download_url}'>Download ZIP</a></p>"
                        f"<p>This link expires in 15 minutes.</p>",
                    )

                return {
                    "job_id": job_id,
                    "status": "completed",
                    "download_url": download_url,
                    "document_count": len(docs),
                }

        result = _run_async(_generate())
        logger.info("bulk_download_completed", extra={"job_id": job_id, "result": result})
        return result

    except Exception as exc:
        logger.exception("generate_bulk_download failed", extra={"job_id": job_id})
        raise self.retry(exc=exc) from exc
