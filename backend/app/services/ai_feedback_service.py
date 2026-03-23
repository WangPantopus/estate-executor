"""AI feedback service — logs user corrections to AI outputs.

When users correct AI classifications or extractions, this service records
the original AI output alongside the user's correction for future
prompt improvement and fine-tuning data collection.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_feedback import AIFeedback

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-20250514"


async def log_classification_correction(
    db: AsyncSession,
    *,
    firm_id: UUID,
    matter_id: UUID,
    document_id: UUID,
    original_doc_type: str | None,
    original_confidence: float | None,
    corrected_doc_type: str,
    corrected_by: UUID | None = None,
) -> AIFeedback:
    """Log when a user corrects or confirms an AI classification."""
    is_correction = original_doc_type is not None and original_doc_type != corrected_doc_type

    feedback = AIFeedback(
        firm_id=firm_id,
        matter_id=matter_id,
        entity_type="document",
        entity_id=document_id,
        feedback_type="classification_correction" if is_correction else "classification_confirmation",
        ai_output={
            "doc_type": original_doc_type,
            "confidence": original_confidence,
        },
        user_correction={
            "doc_type": corrected_doc_type,
        },
        corrected_by=corrected_by,
        model_used=_MODEL,
        metadata_={
            "was_correction": is_correction,
        },
    )
    db.add(feedback)
    await db.flush()

    logger.info(
        "ai_feedback_classification",
        extra={
            "document_id": str(document_id),
            "original_type": original_doc_type,
            "corrected_type": corrected_doc_type,
            "was_correction": is_correction,
        },
    )

    return feedback


async def log_extraction_correction(
    db: AsyncSession,
    *,
    firm_id: UUID,
    matter_id: UUID,
    document_id: UUID,
    original_extracted_data: dict[str, Any] | None,
    corrected_fields: dict[str, Any],
    corrected_by: UUID | None = None,
) -> AIFeedback:
    """Log when a user corrects AI-extracted data fields."""
    # Identify which fields changed
    original = original_extracted_data or {}
    changed_fields = {
        k: {"original": original.get(k), "corrected": v}
        for k, v in corrected_fields.items()
        if original.get(k) != v
    }

    feedback = AIFeedback(
        firm_id=firm_id,
        matter_id=matter_id,
        entity_type="document",
        entity_id=document_id,
        feedback_type="extraction_correction",
        ai_output={
            k: v for k, v in original.items()
            if not k.startswith("_")
        },
        user_correction=corrected_fields,
        corrected_by=corrected_by,
        model_used=_MODEL,
        metadata_={
            "changed_fields": list(changed_fields.keys()),
            "change_count": len(changed_fields),
        },
    )
    db.add(feedback)
    await db.flush()

    logger.info(
        "ai_feedback_extraction",
        extra={
            "document_id": str(document_id),
            "changed_field_count": len(changed_fields),
            "changed_fields": list(changed_fields.keys()),
        },
    )

    return feedback
