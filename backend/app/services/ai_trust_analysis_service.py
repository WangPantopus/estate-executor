"""AI trust analysis service — analyzes trust documents to suggest entity creation and funding.

When a trust document is uploaded and extracted, this service:
1. Auto-creates an entity from extracted trust details
2. Suggests which assets should be funded into the trust
3. Flags assets the trust references but aren't in the registry
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.events import event_logger
from app.models.ai_usage_logs import AIUsageLog
from app.models.assets import Asset
from app.models.documents import Document
from app.models.entities import Entity
from app.models.enums import ActorType, EntityType, FundingStatus
from app.models.matters import Matter
from app.schemas.ai import AIExtractResponse
from app.services.ai_rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-20250514"
_INPUT_COST_PER_M = 3.0
_OUTPUT_COST_PER_M = 15.0

# Map extracted trust_type strings to EntityType enum
_TRUST_TYPE_MAP: dict[str, EntityType] = {
    "revocable": EntityType.revocable_trust,
    "revocable trust": EntityType.revocable_trust,
    "revocable living trust": EntityType.revocable_trust,
    "living trust": EntityType.revocable_trust,
    "irrevocable": EntityType.irrevocable_trust,
    "irrevocable trust": EntityType.irrevocable_trust,
    "special needs trust": EntityType.irrevocable_trust,
    "charitable trust": EntityType.irrevocable_trust,
}

_SYSTEM_PROMPT = """You are analyzing a trust document in the context of estate administration. \
Given the extracted trust details and the current asset registry, identify:

1. Which existing assets should be funded into this trust (based on asset type and trust provisions)
2. Any assets or accounts the trust document references that are NOT in the current registry

Be specific and reference actual assets from the registry by their titles."""


def _build_user_prompt(
    *,
    trust_data: dict[str, Any],
    assets_summary: list[dict[str, Any]],
) -> str:
    """Build user prompt for trust funding analysis."""
    trust_lines: list[str] = []
    for key, value in trust_data.items():
        if value is not None and not str(key).startswith("_"):
            trust_lines.append(f"  {key}: {value}")
    trust_section = "\n".join(trust_lines) or "  (no extracted fields)"

    asset_lines = "\n".join(
        f"  - [{a['id'][:8]}] {a['title']} (type: {a['type']}, institution: {a.get('institution', 'N/A')}, value: {a.get('value', 'N/A')}, transfer: {a.get('transfer_mechanism', 'N/A')})"
        for a in assets_summary
    ) or "  (no assets registered)"

    return f"""Analyze this trust document and compare against the asset registry:

Extracted Trust Details:
{trust_section}

Current Asset Registry:
{asset_lines}

For each existing asset, determine if it should be funded into this trust. \
Also identify any accounts or property referenced in the trust provisions \
that are NOT in the asset registry.

Provide your analysis."""


def _build_tool_schema() -> dict[str, Any]:
    return {
        "name": "analyze_trust_funding",
        "description": "Analyze which assets should be funded into a trust",
        "input_schema": {
            "type": "object",
            "properties": {
                "funding_suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "asset_id": {
                                "type": "string",
                                "description": "ID of the existing asset to fund into trust",
                            },
                            "asset_title": {
                                "type": "string",
                                "description": "Title of the asset",
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Why this asset should be funded into the trust",
                            },
                        },
                        "required": ["asset_id", "asset_title", "reasoning"],
                    },
                },
                "missing_assets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Description of the referenced asset/account not in registry",
                            },
                            "source_reference": {
                                "type": "string",
                                "description": "What part of the trust document references this",
                            },
                        },
                        "required": ["description", "source_reference"],
                    },
                },
            },
            "required": ["funding_suggestions", "missing_assets"],
        },
    }


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    input_cost = (input_tokens / 1_000_000) * _INPUT_COST_PER_M
    output_cost = (output_tokens / 1_000_000) * _OUTPUT_COST_PER_M
    return round(input_cost + output_cost, 6)


def _call_claude(user_prompt: str) -> tuple[dict[str, Any], int, int]:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    tool = _build_tool_schema()

    response = client.messages.create(
        model=_MODEL,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        tools=[tool],
        tool_choice={"type": "tool", "name": "analyze_trust_funding"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    tool_result: dict[str, Any] | None = None
    for block in response.content:
        if block.type == "tool_use":
            tool_result = block.input  # type: ignore[assignment]
            break

    if tool_result is None:
        raise ValueError("Claude did not return a tool_use response for trust analysis")

    return tool_result, response.usage.input_tokens, response.usage.output_tokens


async def _log_ai_usage(
    db: AsyncSession,
    *,
    firm_id: UUID,
    matter_id: UUID,
    operation: str,
    input_tokens: int,
    output_tokens: int,
    cost_estimate: float,
    status: str = "success",
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    log_entry = AIUsageLog(
        firm_id=firm_id,
        matter_id=matter_id,
        document_id=None,
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


def _resolve_trust_type(extracted_type: str | None) -> EntityType:
    """Map an extracted trust_type string to an EntityType enum value."""
    if not extracted_type:
        return EntityType.revocable_trust
    normalized = extracted_type.strip().lower()
    return _TRUST_TYPE_MAP.get(normalized, EntityType.revocable_trust)


async def analyze_trust_document(
    db: AsyncSession,
    *,
    document_id: UUID,
    matter_id: UUID,
) -> dict[str, Any]:
    """Analyze a trust document and return funding analysis.

    1. Validates the document is a classified trust_document with extracted data
    2. Optionally auto-creates an entity from extracted trust details
    3. Analyzes which assets should be funded into the trust
    4. Returns funding suggestions and missing asset references
    """
    # Fetch document
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.matter_id == matter_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise ValueError(f"Document {document_id} not found")
    if doc.doc_type != "trust_document":
        raise ValueError(f"Document {document_id} is not a trust document (type: {doc.doc_type})")

    # Fetch matter
    matter_result = await db.execute(select(Matter).where(Matter.id == matter_id))
    matter = matter_result.scalar_one_or_none()
    if matter is None:
        raise ValueError(f"Matter {matter_id} not found")

    check_rate_limit(firm_id=matter.firm_id, matter_id=matter.id)

    # Get extracted trust data
    extracted = doc.ai_extracted_data or {}
    trust_data = {
        k: v for k, v in extracted.items()
        if not k.startswith("_") and k not in ("classification_status", "extraction_status")
        and v is not None
    }

    # Auto-create entity if trust_name is available and no matching entity exists
    entity_created = False
    entity_id: UUID | None = None
    trust_name = trust_data.get("trust_name")

    if trust_name:
        existing = await db.execute(
            select(Entity).where(Entity.matter_id == matter_id, Entity.name == trust_name)
        )
        if existing.scalar_one_or_none() is None:
            entity_type = _resolve_trust_type(trust_data.get("trust_type"))
            new_entity = Entity(
                matter_id=matter_id,
                entity_type=entity_type,
                name=trust_name,
                trustee=trust_data.get("trustee"),
                successor_trustee=trust_data.get("successor_trustee"),
                funding_status=FundingStatus.unknown,
                distribution_rules={
                    "provisions": trust_data.get("distribution_provisions"),
                    "special_provisions": trust_data.get("special_provisions", []),
                    "spendthrift_clause": trust_data.get("spendthrift_clause", False),
                    "special_needs_provisions": trust_data.get("special_needs_provisions", False),
                },
                metadata_={"source_document_id": str(document_id)},
            )
            db.add(new_entity)
            await db.flush()
            entity_id = new_entity.id
            entity_created = True

            await event_logger.log(
                db,
                matter_id=matter_id,
                actor_id=None,
                actor_type=ActorType.ai,
                entity_type="entity",
                entity_id=new_entity.id,
                action="created",
                metadata={
                    "name": trust_name,
                    "entity_type": entity_type.value,
                    "auto_created_from_document": str(document_id),
                },
            )

    # Gather assets for funding analysis
    assets_result = await db.execute(
        select(Asset).where(Asset.matter_id == matter_id)
    )
    assets = list(assets_result.scalars().all())
    assets_summary = [
        {
            "id": str(a.id),
            "title": a.title,
            "type": a.asset_type.value if hasattr(a.asset_type, "value") else str(a.asset_type),
            "institution": a.institution or "N/A",
            "value": f"${a.current_estimated_value:,.2f}" if a.current_estimated_value else "Unknown",
            "transfer_mechanism": a.transfer_mechanism.value if hasattr(a.transfer_mechanism, "value") else str(a.transfer_mechanism),
        }
        for a in assets
    ]

    # Call Claude for funding analysis
    user_prompt = _build_user_prompt(trust_data=trust_data, assets_summary=assets_summary)

    try:
        parsed_result, input_tokens, output_tokens = _call_claude(user_prompt)
    except Exception as exc:
        await _log_ai_usage(
            db,
            firm_id=matter.firm_id,
            matter_id=matter.id,
            operation="trust_analysis",
            input_tokens=0,
            output_tokens=0,
            cost_estimate=0.0,
            status="error",
            error_message=str(exc),
        )
        raise

    cost_estimate = _estimate_cost(input_tokens, output_tokens)

    await _log_ai_usage(
        db,
        firm_id=matter.firm_id,
        matter_id=matter.id,
        operation="trust_analysis",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_estimate=cost_estimate,
        metadata={
            "document_id": str(document_id),
            "entity_created": entity_created,
            "funding_suggestions": len(parsed_result.get("funding_suggestions", [])),
            "missing_assets": len(parsed_result.get("missing_assets", [])),
        },
    )

    await event_logger.log(
        db,
        matter_id=matter.id,
        actor_id=None,
        actor_type=ActorType.ai,
        entity_type="document",
        entity_id=document_id,
        action="trust_analyzed",
        metadata={
            "entity_created": entity_created,
            "entity_id": str(entity_id) if entity_id else None,
            "model": _MODEL,
        },
    )

    return {
        "entity_created": entity_created,
        "entity_id": str(entity_id) if entity_id else None,
        "trust_name": trust_name,
        "funding_suggestions": parsed_result.get("funding_suggestions", []),
        "missing_assets": parsed_result.get("missing_assets", []),
    }
