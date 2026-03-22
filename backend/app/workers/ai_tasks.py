"""AI tasks — document classification, extraction, letter drafting.

Placeholder implementations — will be filled in during the AI phase.
"""

from __future__ import annotations

import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.ai_tasks.classify_document",
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=900,
    soft_time_limit=120,
    time_limit=180,
)
def classify_document(self, document_id: str, matter_id: str):
    """Classify an uploaded document using AI.

    Placeholder: In production, this would:
    1. Download the document from S3
    2. Send to AI model for classification
    3. Update the document record with doc_type and confidence
    4. Optionally trigger extract_document_data
    """
    try:
        logger.info(
            "classify_document_placeholder",
            extra={
                "document_id": document_id,
                "matter_id": matter_id,
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
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.ai_tasks.extract_document_data",
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=900,
    soft_time_limit=120,
    time_limit=180,
)
def extract_document_data(self, document_id: str):
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
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.ai_tasks.draft_letter",
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=900,
    soft_time_limit=180,
    time_limit=300,
)
def draft_letter(self, matter_id: str, asset_id: str, letter_type: str):
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
        raise self.retry(exc=exc)
