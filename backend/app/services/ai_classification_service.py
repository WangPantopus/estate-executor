"""AI document classification service — classifies documents using Claude API.

Fetches document from S3, extracts text, sends to Claude for classification,
updates the document record, and logs the AI event.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.core.config import settings
from app.core.events import event_logger
from app.models.ai_usage_logs import AIUsageLog
from app.models.documents import Document
from app.models.enums import ActorType
from app.models.matters import Matter
from app.prompts import get_prompt_version
from app.prompts.classification import DOCUMENT_TYPES as DOCUMENT_TYPES
from app.prompts.classification import SYSTEM_PROMPT as _SYSTEM_PROMPT
from app.prompts.classification import build_tool_schema as _build_tool_schema
from app.prompts.classification import (
    build_user_prompt as _build_classification_prompt,
)
from app.schemas.ai import AIClassifyResponse
from app.services import text_extraction_service
from app.services.ai_rate_limiter import check_rate_limit

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-20250514"
_INPUT_COST_PER_M = 3.0
_OUTPUT_COST_PER_M = 15.0


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate the cost of a Claude API call in USD."""
    input_cost = (input_tokens / 1_000_000) * _INPUT_COST_PER_M
    output_cost = (output_tokens / 1_000_000) * _OUTPUT_COST_PER_M
    return round(input_cost + output_cost, 6)


def _call_claude(
    user_prompt: str,
) -> tuple[dict[str, Any], int, int]:
    """Call the Claude API with the classification prompt.

    Returns (parsed_result, input_tokens, output_tokens).
    """
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    tool = _build_tool_schema()

    response = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        tools=[tool],
        tool_choice={"type": "tool", "name": "classify_document"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    # Extract tool use result from response
    tool_result: dict[str, Any] | None = None
    for block in response.content:
        if block.type == "tool_use":
            tool_result = block.input  # type: ignore[assignment]
            break

    if tool_result is None:
        raise ValueError("Claude did not return a tool_use response")

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    return tool_result, input_tokens, output_tokens


async def _log_ai_usage(
    db: AsyncSession,
    *,
    firm_id: UUID,
    matter_id: UUID,
    document_id: UUID | None,
    operation: str,
    input_tokens: int,
    output_tokens: int,
    cost_estimate: float,
    status: str = "success",
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log AI API usage to the ai_usage_logs table."""
    log_entry = AIUsageLog(
        firm_id=firm_id,
        matter_id=matter_id,
        document_id=document_id,
        operation=operation,
        model=_MODEL,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_estimate_usd=cost_estimate,
        status=status,
        error_message=error_message,
        metadata_=metadata or {},
    )
    db.add(log_entry)
    await db.flush()


async def classify_document(
    db: AsyncSession,
    *,
    document_id: UUID,
) -> AIClassifyResponse:
    """Classify a document using Claude AI.

    1. Fetches document record and matter context from DB
    2. Downloads and extracts text from the document
    3. Checks rate limits
    4. Calls Claude API for classification
    5. Updates document record with classification result
    6. Logs AI event and usage
    """
    # Fetch document
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise ValueError(f"Document {document_id} not found")

    # Fetch matter context
    matter_result = await db.execute(select(Matter).where(Matter.id == doc.matter_id))
    matter = matter_result.scalar_one_or_none()
    if matter is None:
        raise ValueError(f"Matter {doc.matter_id} not found for document {document_id}")

    # Check rate limits
    check_rate_limit(firm_id=matter.firm_id, matter_id=matter.id)

    # Extract text
    extracted_text = text_extraction_service.extract_text(
        storage_key=doc.storage_key,
        mime_type=doc.mime_type,
    )

    if not extracted_text:
        # Log the failure and return a low-confidence "other"
        await _log_ai_usage(
            db,
            firm_id=matter.firm_id,
            matter_id=matter.id,
            document_id=doc.id,
            operation="classify",
            input_tokens=0,
            output_tokens=0,
            cost_estimate=0.0,
            status="error",
            error_message="Text extraction returned empty result",
        )
        fallback = AIClassifyResponse(
            doc_type="other",
            confidence=0.0,
            reasoning="Could not extract text from document",
        )
        doc.doc_type = fallback.doc_type
        doc.doc_type_confidence = fallback.confidence
        await db.flush()
        return fallback

    # Build prompt with matter context
    user_prompt = _build_classification_prompt(
        extracted_text,
        estate_type=matter.estate_type.value if hasattr(matter.estate_type, "value") else str(matter.estate_type) if matter.estate_type else None,
        jurisdiction=matter.jurisdiction_state,
        decedent_name=matter.decedent_name,
    )

    # Call Claude API
    try:
        parsed_result, input_tokens, output_tokens = _call_claude(user_prompt)
    except Exception as exc:
        await _log_ai_usage(
            db,
            firm_id=matter.firm_id,
            matter_id=matter.id,
            document_id=doc.id,
            operation="classify",
            input_tokens=0,
            output_tokens=0,
            cost_estimate=0.0,
            status="error",
            error_message=str(exc),
        )
        raise

    cost_estimate = _estimate_cost(input_tokens, output_tokens)

    # Parse and validate response
    classification = AIClassifyResponse(
        doc_type=parsed_result["doc_type"],
        confidence=parsed_result["confidence"],
        reasoning=parsed_result["reasoning"],
    )

    # Update document record
    doc.doc_type = classification.doc_type
    doc.doc_type_confidence = classification.confidence
    await db.flush()

    # Log AI usage
    await _log_ai_usage(
        db,
        firm_id=matter.firm_id,
        matter_id=matter.id,
        document_id=doc.id,
        operation="classify",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_estimate=cost_estimate,
        metadata={
            "doc_type": classification.doc_type,
            "confidence": classification.confidence,
        },
    )

    # Log audit event
    await event_logger.log(
        db,
        matter_id=matter.id,
        actor_id=None,
        actor_type=ActorType.ai,
        entity_type="document",
        entity_id=doc.id,
        action="classified",
        changes={
            "doc_type": {"old": None, "new": classification.doc_type},
            "doc_type_confidence": {"old": None, "new": classification.confidence},
        },
        metadata={
            "reasoning": classification.reasoning,
            "model": _MODEL,
            "prompt_version": get_prompt_version("classify"),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    )

    logger.info(
        "document_classified",
        extra={
            "document_id": str(document_id),
            "doc_type": classification.doc_type,
            "confidence": classification.confidence,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_estimate_usd": cost_estimate,
        },
    )

    return classification
