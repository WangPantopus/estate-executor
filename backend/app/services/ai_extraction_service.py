"""AI document data extraction service — extracts structured data per doc type.

After classification, this service extracts specific fields from documents
based on their type using Claude API with structured tool_use output.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.core.config import settings
from app.core.events import event_logger
from app.models.ai_usage_logs import AIUsageLog
from app.models.documents import Document
from app.models.enums import ActorType
from app.models.matters import Matter
from app.prompts import get_prompt_version
from app.schemas.ai import AIExtractResponse
from app.services import text_extraction_service
from app.services.ai_rate_limiter import check_rate_limit

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-20250514"
_INPUT_COST_PER_M = 3.0
_OUTPUT_COST_PER_M = 15.0

# ─── Per-type extraction schemas ──────────────────────────────────────────────

EXTRACTION_SCHEMAS: dict[str, dict[str, Any]] = {
    "account_statement": {
        "properties": {
            "institution": {
                "type": "string",
                "description": "Name of the financial institution (bank, brokerage, etc.)",
            },
            "account_type": {
                "type": "string",
                "description": "Type of account (checking, savings, brokerage, etc.)",
            },
            "account_number_last4": {
                "type": "string",
                "description": "Last 4 digits of the account number only",
            },
            "balance": {
                "type": "number",
                "description": "Current or closing balance amount",
            },
            "as_of_date": {
                "type": "string",
                "description": "Statement date or as-of date in YYYY-MM-DD format",
            },
        },
        "required": ["institution", "account_type", "account_number_last4", "balance", "as_of_date"],
    },
    "deed": {
        "properties": {
            "property_address": {
                "type": "string",
                "description": "Full property street address",
            },
            "grantee": {
                "type": "string",
                "description": "Name of the grantee (person receiving the property)",
            },
            "recording_date": {
                "type": "string",
                "description": "Date the deed was recorded in YYYY-MM-DD format",
            },
            "parcel_number": {
                "type": "string",
                "description": "Assessor's parcel number (APN)",
            },
            "property_type": {
                "type": "string",
                "description": "Type of property (residential, commercial, land, etc.)",
            },
        },
        "required": ["property_address", "grantee", "recording_date", "parcel_number", "property_type"],
    },
    "insurance_policy": {
        "properties": {
            "carrier": {
                "type": "string",
                "description": "Insurance company name",
            },
            "policy_number": {
                "type": "string",
                "description": "Policy number",
            },
            "face_value": {
                "type": "number",
                "description": "Face value / death benefit amount",
            },
            "beneficiary_name": {
                "type": "string",
                "description": "Name of the designated beneficiary",
            },
            "policy_type": {
                "type": "string",
                "enum": ["term", "whole", "universal", "other"],
                "description": "Type of life insurance policy",
            },
        },
        "required": ["carrier", "policy_number", "face_value", "beneficiary_name", "policy_type"],
    },
    "trust_document": {
        "properties": {
            "trust_name": {
                "type": "string",
                "description": "Name of the trust",
            },
            "trust_type": {
                "type": "string",
                "description": "Type of trust (revocable, irrevocable, etc.)",
            },
            "trustee": {
                "type": "string",
                "description": "Name of the current trustee",
            },
            "successor_trustee": {
                "type": "string",
                "description": "Name of the successor trustee",
            },
            "date_established": {
                "type": "string",
                "description": "Date the trust was established in YYYY-MM-DD format",
            },
            "distribution_provisions": {
                "type": "string",
                "description": "Summary of distribution provisions",
            },
            "special_provisions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of special provisions found in the trust document",
            },
            "spendthrift_clause": {
                "type": "boolean",
                "description": "Whether a spendthrift clause is present",
            },
            "special_needs_provisions": {
                "type": "boolean",
                "description": "Whether special needs trust provisions are present",
            },
        },
        "required": [
            "trust_name", "trust_type", "trustee", "successor_trustee",
            "date_established", "distribution_provisions", "special_provisions",
            "spendthrift_clause", "special_needs_provisions",
        ],
    },
    "appraisal": {
        "properties": {
            "property_description": {
                "type": "string",
                "description": "Description of the appraised property",
            },
            "appraised_value": {
                "type": "number",
                "description": "Appraised value amount",
            },
            "appraisal_date": {
                "type": "string",
                "description": "Date of appraisal in YYYY-MM-DD format",
            },
            "appraiser_name": {
                "type": "string",
                "description": "Name of the appraiser",
            },
        },
        "required": ["property_description", "appraised_value", "appraisal_date", "appraiser_name"],
    },
    "tax_return": {
        "properties": {
            "tax_year": {
                "type": "integer",
                "description": "Tax year for this return",
            },
            "return_type": {
                "type": "string",
                "description": "Type of return (1040, 1041, 706, etc.)",
            },
            "gross_income": {
                "type": "number",
                "description": "Total or gross income amount",
            },
            "tax_liability": {
                "type": "number",
                "description": "Total tax liability amount",
            },
        },
        "required": ["tax_year", "return_type", "gross_income", "tax_liability"],
    },
}

# Doc types that support extraction
EXTRACTABLE_TYPES = set(EXTRACTION_SCHEMAS.keys())


def _build_extraction_tool(doc_type: str) -> dict[str, Any]:
    """Build the tool-use schema for a specific document type."""
    schema = EXTRACTION_SCHEMAS[doc_type]
    # Make all properties nullable (allow null if not found)
    nullable_props: dict[str, Any] = {}
    for field_name, field_spec in schema["properties"].items():
        nullable_props[field_name] = {**field_spec, "description": field_spec["description"] + ". Set to null if not present or unclear."}
        # Allow null for all types
        if "type" in field_spec and field_spec["type"] != "array" and field_spec["type"] != "boolean":
            nullable_props[field_name]["type"] = [field_spec["type"], "null"]

    return {
        "name": "extract_data",
        "description": f"Extract structured data from a {doc_type.replace('_', ' ')} document",
        "input_schema": {
            "type": "object",
            "properties": {
                "extracted_fields": {
                    "type": "object",
                    "properties": nullable_props,
                    "required": schema["required"],
                    "description": "Extracted fields from the document",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Overall confidence in the extraction quality",
                },
            },
            "required": ["extracted_fields", "confidence"],
        },
    }


def _build_extraction_prompt(extracted_text: str, doc_type: str) -> tuple[str, str]:
    """Build the system and user prompts for extraction.

    Returns (system_prompt, user_prompt).
    """
    doc_type_display = doc_type.replace("_", " ")
    schema = EXTRACTION_SCHEMAS[doc_type]
    field_list = "\n".join(
        f"- {name}: {spec['description']}"
        for name, spec in schema["properties"].items()
    )

    system_prompt = (
        f"You are extracting structured data from a {doc_type_display} "
        f"for estate administration. Extract the requested fields from the document text. "
        f"If a field is not present or unclear, set it to null. Do not guess."
    )

    user_prompt = f"""Extract the following fields from this {doc_type_display}:

{field_list}

Document text:
<document_text>
{extracted_text}
</document_text>

Extract all available fields. For any field that is not clearly present in the document, set the value to null."""

    return system_prompt, user_prompt


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate the cost of a Claude API call in USD."""
    input_cost = (input_tokens / 1_000_000) * _INPUT_COST_PER_M
    output_cost = (output_tokens / 1_000_000) * _OUTPUT_COST_PER_M
    return round(input_cost + output_cost, 6)


def _call_claude(system_prompt: str, user_prompt: str, tool: dict[str, Any]) -> tuple[dict[str, Any], int, int]:
    """Call Claude API for extraction. Returns (result, input_tokens, output_tokens)."""
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    response = client.messages.create(
        model=_MODEL,
        max_tokens=2048,
        system=system_prompt,
        tools=[tool],
        tool_choice={"type": "tool", "name": "extract_data"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    tool_result: dict[str, Any] | None = None
    for block in response.content:
        if block.type == "tool_use":
            tool_result = block.input  # type: ignore[assignment]
            break

    if tool_result is None:
        raise ValueError("Claude did not return a tool_use response for extraction")

    return tool_result, response.usage.input_tokens, response.usage.output_tokens


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


async def extract_document_data(
    db: AsyncSession,
    *,
    document_id: UUID,
) -> AIExtractResponse:
    """Extract structured data from a classified document.

    1. Validates the document is classified and extractable
    2. Downloads and extracts text
    3. Checks rate limits
    4. Calls Claude with type-specific extraction prompt
    5. Stores extracted data in document.ai_extracted_data
    6. Logs AI event and usage
    """
    # Fetch document
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise ValueError(f"Document {document_id} not found")

    if not doc.doc_type:
        raise ValueError(f"Document {document_id} has not been classified yet")

    if doc.doc_type not in EXTRACTABLE_TYPES:
        raise ValueError(
            f"Document type '{doc.doc_type}' does not support extraction. "
            f"Supported types: {', '.join(sorted(EXTRACTABLE_TYPES))}"
        )

    # Fetch matter context
    matter_result = await db.execute(select(Matter).where(Matter.id == doc.matter_id))
    matter = matter_result.scalar_one_or_none()
    if matter is None:
        raise ValueError(f"Matter {doc.matter_id} not found")

    # Check rate limits
    check_rate_limit(firm_id=matter.firm_id, matter_id=matter.id)

    # Extract text
    extracted_text = text_extraction_service.extract_text(
        storage_key=doc.storage_key,
        mime_type=doc.mime_type,
    )

    if not extracted_text:
        await _log_ai_usage(
            db,
            firm_id=matter.firm_id,
            matter_id=matter.id,
            document_id=doc.id,
            operation="extract",
            input_tokens=0,
            output_tokens=0,
            cost_estimate=0.0,
            status="error",
            error_message="Text extraction returned empty result",
        )
        fallback = AIExtractResponse(extracted_fields={}, confidence=0.0)
        doc.ai_extracted_data = {"extraction_status": "failed", "reason": "empty_text"}
        await db.flush()
        return fallback

    # Build prompts and tool
    system_prompt, user_prompt = _build_extraction_prompt(extracted_text, doc.doc_type)
    tool = _build_extraction_tool(doc.doc_type)

    # Call Claude API
    try:
        parsed_result, input_tokens, output_tokens = _call_claude(
            system_prompt, user_prompt, tool
        )
    except Exception as exc:
        await _log_ai_usage(
            db,
            firm_id=matter.firm_id,
            matter_id=matter.id,
            document_id=doc.id,
            operation="extract",
            input_tokens=0,
            output_tokens=0,
            cost_estimate=0.0,
            status="error",
            error_message=str(exc),
        )
        raise

    cost_estimate = _estimate_cost(input_tokens, output_tokens)

    # Parse response
    extracted_fields = parsed_result.get("extracted_fields", {})
    confidence = parsed_result.get("confidence", 0.0)

    response = AIExtractResponse(
        extracted_fields=extracted_fields,
        confidence=confidence,
    )

    # Store in document's ai_extracted_data with metadata
    doc.ai_extracted_data = {
        **extracted_fields,
        "_extraction_metadata": {
            "model": _MODEL,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "confidence": confidence,
            "doc_type": doc.doc_type,
            "prompt_version": get_prompt_version("extract"),
            "extracted_at": datetime.now(UTC).isoformat(),
        },
    }
    await db.flush()

    # Log AI usage
    await _log_ai_usage(
        db,
        firm_id=matter.firm_id,
        matter_id=matter.id,
        document_id=doc.id,
        operation="extract",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_estimate=cost_estimate,
        metadata={
            "doc_type": doc.doc_type,
            "fields_extracted": list(extracted_fields.keys()),
            "confidence": confidence,
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
        action="data_extracted",
        changes={
            "ai_extracted_data": {
                "old": None,
                "new": "extracted",
            },
        },
        metadata={
            "doc_type": doc.doc_type,
            "fields_extracted": list(extracted_fields.keys()),
            "confidence": confidence,
            "model": _MODEL,
        },
    )

    logger.info(
        "document_data_extracted",
        extra={
            "document_id": str(document_id),
            "doc_type": doc.doc_type,
            "fields_extracted": list(extracted_fields.keys()),
            "confidence": confidence,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_estimate_usd": cost_estimate,
        },
    )

    return response
