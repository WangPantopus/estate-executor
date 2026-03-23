"""AI tasks — document classification, extraction, letter drafting.

All three AI operations are fully implemented via their respective services:
- ai_classification_service — document classification
- ai_extraction_service — structured data extraction
- ai_letter_service — formal letter drafting
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Minimum classification confidence to auto-trigger extraction
_AUTO_EXTRACT_CONFIDENCE_THRESHOLD = 0.7


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
    6. If confidence > 0.7 and type is extractable, chains extraction
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
                    await _mark_classification_failed(session, document_id, matter_id)
                    raise

        classification_result = _run_async(_classify())

        # Chain extraction if confidence is high enough and type is extractable
        doc_type = classification_result.get("doc_type")
        confidence = classification_result.get("confidence", 0.0)

        if (
            doc_type
            and confidence >= _AUTO_EXTRACT_CONFIDENCE_THRESHOLD
        ):
            from app.services.ai_extraction_service import EXTRACTABLE_TYPES

            if doc_type in EXTRACTABLE_TYPES:
                logger.info(
                    "auto_triggering_extraction",
                    extra={
                        "document_id": document_id,
                        "doc_type": doc_type,
                        "confidence": confidence,
                    },
                )
                extract_document_data.delay(document_id, matter_id)

        return classification_result

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
def extract_document_data(self: Any, document_id: str, matter_id: str = "") -> dict[str, Any]:
    """Extract structured data from a classified document using AI.

    1. Validates the document is classified and extractable
    2. Downloads and extracts text
    3. Calls Claude with type-specific extraction prompt
    4. Stores extracted data in document.ai_extracted_data
    5. Emits WebSocket notification
    """
    try:
        logger.info(
            "extract_document_data_started",
            extra={"document_id": document_id, "matter_id": matter_id},
        )

        async def _extract() -> dict[str, Any]:
            from app.core.database import async_session_factory
            from app.realtime.publisher import publish_realtime_event
            from app.services.ai_extraction_service import extract_document_data as do_extract

            async with async_session_factory() as session:
                try:
                    result = await do_extract(session, document_id=UUID(document_id))
                    await session.commit()

                    # Emit WebSocket event
                    if matter_id:
                        publish_realtime_event(
                            matter_id=matter_id,
                            event="document_data_extracted",
                            data={
                                "document_id": document_id,
                                "extracted_fields": {
                                    k: v
                                    for k, v in result.extracted_fields.items()
                                    if v is not None
                                },
                                "confidence": result.confidence,
                            },
                        )

                    return {
                        "document_id": document_id,
                        "status": "extracted",
                        "fields_count": len(
                            [v for v in result.extracted_fields.values() if v is not None]
                        ),
                        "confidence": result.confidence,
                    }
                except Exception:
                    await session.rollback()
                    raise

        return _run_async(_extract())

    except Exception as exc:
        logger.exception(
            "extract_document_data_failed",
            extra={"document_id": document_id},
        )
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
    """Draft a letter using AI for estate administration.

    Gathers matter context, asset details, and executor info, then calls
    Claude to generate a professional notification or claim letter.
    """
    try:
        logger.info(
            "draft_letter_started",
            extra={
                "matter_id": matter_id,
                "asset_id": asset_id,
                "letter_type": letter_type,
            },
        )

        async def _draft() -> dict[str, Any]:
            from app.core.database import async_session_factory
            from app.services.ai_letter_service import draft_letter as do_draft

            async with async_session_factory() as session:
                result = await do_draft(
                    session,
                    matter_id=UUID(matter_id),
                    asset_id=UUID(asset_id),
                    letter_type=letter_type,
                )
                await session.commit()

                return {
                    "matter_id": matter_id,
                    "asset_id": asset_id,
                    "letter_type": letter_type,
                    "status": "drafted",
                    "subject": result.subject,
                    "recipient_institution": result.recipient_institution,
                }

        return _run_async(_draft())

    except Exception as exc:
        logger.exception("draft_letter failed")
        raise self.retry(exc=exc) from exc
