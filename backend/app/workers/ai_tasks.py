"""AI tasks — document classification, extraction, letter drafting.

Classification is fully implemented via the ai_classification_service.
Extraction and letter drafting remain placeholders for future implementation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """Run an async coroutine in a new event loop (Celery workers are sync)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.ai_tasks.classify_document",
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=900,
    soft_time_limit=120,
    time_limit=180,
)
def classify_document(self: Any, document_id: str, matter_id: str) -> dict[str, Any]:
    """Classify an uploaded document using AI.

    1. Downloads the document from S3
    2. Extracts text (PDF/image/DOCX)
    3. Sends to Claude API for classification
    4. Updates the document record with doc_type and confidence
    5. Logs AI event and emits WebSocket notification
    """
    try:
        logger.info(
            "classify_document_started",
            extra={"document_id": document_id, "matter_id": matter_id},
        )

        async def _classify() -> dict[str, Any]:
            from app.core.database import async_session_factory
            from app.realtime.publisher import publish_realtime_event
            from app.services.ai_classification_service import classify_document as do_classify

            async with async_session_factory() as session:
                try:
                    result = await do_classify(session, document_id=UUID(document_id))
                    await session.commit()

                    # Emit WebSocket event for real-time UI update
                    publish_realtime_event(
                        matter_id=matter_id,
                        event="document_classified",
                        data={
                            "document_id": document_id,
                            "doc_type": result.doc_type,
                            "confidence": result.confidence,
                            "reasoning": result.reasoning,
                        },
                    )

                    return {
                        "document_id": document_id,
                        "status": "classified",
                        "doc_type": result.doc_type,
                        "confidence": result.confidence,
                    }
                except Exception:
                    await session.rollback()
                    # Mark classification as failed in document metadata
                    await _mark_classification_failed(session, document_id, matter_id)
                    raise

        return _run_async(_classify())

    except Exception as exc:
        logger.exception(
            "classify_document_failed",
            extra={"document_id": document_id, "matter_id": matter_id},
        )
        raise self.retry(exc=exc) from exc


async def _mark_classification_failed(
    session: Any, document_id: str, matter_id: str
) -> None:
    """Mark a document as classification_failed in its metadata."""
    try:
        from sqlalchemy import select
        from sqlalchemy.dialects.postgresql import JSONB

        from app.models.documents import Document

        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if doc is not None:
            current_meta = doc.ai_extracted_data or {}
            current_meta["classification_status"] = "failed"
            doc.ai_extracted_data = current_meta
            await session.commit()
    except Exception:
        logger.warning(
            "mark_classification_failed_error",
            extra={"document_id": document_id},
            exc_info=True,
        )


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.ai_tasks.extract_document_data",
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=900,
    soft_time_limit=120,
    time_limit=180,
)
def extract_document_data(self: Any, document_id: str) -> dict[str, Any]:
    """Extract structured data from a document using AI.

    Placeholder: In production, this would parse the document content
    and extract fields like dates, names, amounts, etc.
    """
    try:
        logger.info(
            "extract_document_data_placeholder",
            extra={"document_id": document_id},
        )
        return {
            "document_id": document_id,
            "status": "extracted",
            "extracted_data": None,
        }
    except Exception as exc:
        logger.exception("extract_document_data failed")
        raise self.retry(exc=exc) from exc


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.ai_tasks.draft_letter",
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=900,
    soft_time_limit=180,
    time_limit=300,
)
def draft_letter(self: Any, matter_id: str, asset_id: str, letter_type: str) -> dict[str, Any]:
    """Draft a letter using AI (e.g., notification to creditors, beneficiary communication).

    Placeholder: In production, this would generate a letter draft
    based on matter context, asset details, and letter type template.
    """
    try:
        logger.info(
            "draft_letter_placeholder",
            extra={
                "matter_id": matter_id,
                "asset_id": asset_id,
                "letter_type": letter_type,
            },
        )
        return {
            "matter_id": matter_id,
            "asset_id": asset_id,
            "letter_type": letter_type,
            "status": "drafted",
            "draft_content": None,
        }
    except Exception as exc:
        logger.exception("draft_letter failed")
        raise self.retry(exc=exc) from exc
