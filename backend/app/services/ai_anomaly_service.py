"""AI anomaly detection service — compares documents against asset registry.

Analyzes AI-extracted document data and compares it against registered assets,
stakeholders, and tasks to identify discrepancies, missing entries, and
potential issues.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.core.events import event_logger
from app.models.ai_usage_logs import AIUsageLog
from app.models.assets import Asset
from app.models.documents import Document
from app.models.enums import ActorType
from app.models.matters import Matter
from app.models.stakeholders import Stakeholder
from app.models.tasks import Task
from app.prompts import get_prompt_version
from app.schemas.ai import AIAnomalyResponse, Anomaly
from app.services.ai_rate_limiter import check_rate_limit

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-20250514"
_INPUT_COST_PER_M = 3.0
_OUTPUT_COST_PER_M = 15.0

_SYSTEM_PROMPT = """You are an estate administration auditor. \
Your job is to detect anomalies, discrepancies, and potential issues \
by comparing document-extracted data against the registered asset registry, \
stakeholder list, and task list.

Look for these types of anomalies:
1. MISSING_ASSET: Document mentions an account/asset at an institution not in the asset registry
2. VALUE_DISCREPANCY: Document shows a value that differs >10% from the registered asset value
3. MISSING_STAKEHOLDER: Trust or insurance document names a person not in the stakeholder list
4. MISSING_TASK: An asset exists that should trigger a task (e.g., insurance policy with no claim task)
5. DATA_INCONSISTENCY: Conflicting information between documents or between document and registry

Severity levels: high, medium, low
- high: likely requires immediate attention (e.g., large value discrepancy, missing major asset)
- medium: should be reviewed (e.g., beneficiary not listed, missing task)
- low: informational (e.g., minor inconsistency)"""


def _build_user_prompt(
    *,
    documents_data: list[dict[str, Any]],
    assets_summary: list[dict[str, Any]],
    existing_tasks: list[str],
    stakeholder_names: list[str],
) -> str:
    """Build the user prompt with data to compare."""
    doc_lines: list[str] = []
    for d in documents_data:
        doc_lines.append(f"  Document: {d['filename']} (type: {d['doc_type']})")
        for field, value in d.get("extracted_data", {}).items():
            if value is not None and not str(field).startswith("_"):
                doc_lines.append(f"    {field}: {value}")
        doc_lines.append("")
    doc_section = "\n".join(doc_lines) or "  (no documents with extracted data)"

    asset_lines = "\n".join(
        f"  - [{a['id'][:8]}] {a['title']} (type: {a['type']}, institution: {a.get('institution', 'N/A')}, value: {a.get('value', 'N/A')})"
        for a in assets_summary
    ) or "  (no assets)"

    task_lines = "\n".join(f"  - {t}" for t in existing_tasks) or "  (no tasks)"
    stakeholder_lines = ", ".join(stakeholder_names) if stakeholder_names else "(none)"

    return f"""Compare the following document-extracted data against the asset registry, \
task list, and stakeholder list. Identify any anomalies or discrepancies.

AI-Extracted Document Data:
{doc_section}

Registered Asset Registry:
{asset_lines}

Existing Tasks:
{task_lines}

Registered Stakeholders: {stakeholder_lines}

Analyze all data and report any anomalies found. For each anomaly:
- Identify the type (missing_asset, value_discrepancy, missing_stakeholder, missing_task, data_inconsistency)
- Provide a clear description
- Assign a severity (high, medium, low)
- Reference the relevant document_id and/or asset_id when applicable

If no anomalies are found, return an empty list."""


def _build_tool_schema() -> dict[str, Any]:
    """Build the tool-use schema for structured anomaly output."""
    return {
        "name": "report_anomalies",
        "description": "Report detected anomalies in estate data",
        "input_schema": {
            "type": "object",
            "properties": {
                "anomalies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": [
                                    "missing_asset",
                                    "value_discrepancy",
                                    "missing_stakeholder",
                                    "missing_task",
                                    "data_inconsistency",
                                ],
                                "description": "Type of anomaly detected",
                            },
                            "description": {
                                "type": "string",
                                "description": "Clear description of the anomaly",
                            },
                            "document_id": {
                                "type": ["string", "null"],
                                "description": "ID of the relevant document, or null",
                            },
                            "asset_id": {
                                "type": ["string", "null"],
                                "description": "ID of the relevant asset, or null",
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "Severity level",
                            },
                        },
                        "required": ["type", "description", "severity"],
                    },
                    "description": "List of detected anomalies",
                },
            },
            "required": ["anomalies"],
        },
    }


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    input_cost = (input_tokens / 1_000_000) * _INPUT_COST_PER_M
    output_cost = (output_tokens / 1_000_000) * _OUTPUT_COST_PER_M
    return round(input_cost + output_cost, 6)


def _call_claude(user_prompt: str) -> tuple[dict[str, Any], int, int]:
    """Call Claude API. Returns (result, input_tokens, output_tokens)."""
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    tool = _build_tool_schema()

    response = client.messages.create(
        model=_MODEL,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        tools=[tool],
        tool_choice={"type": "tool", "name": "report_anomalies"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    tool_result: dict[str, Any] | None = None
    for block in response.content:
        if block.type == "tool_use":
            tool_result = block.input  # type: ignore[assignment]
            break

    if tool_result is None:
        raise ValueError("Claude did not return a tool_use response for anomaly detection")

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


async def detect_anomalies(
    db: AsyncSession,
    *,
    matter_id: UUID,
) -> AIAnomalyResponse:
    """Detect anomalies by comparing documents against asset registry.

    1. Gathers all documents with AI-extracted data
    2. Gathers asset registry, tasks, stakeholders
    3. Sends to Claude for anomaly detection
    4. Logs usage and audit event
    """
    # Fetch matter
    matter_result = await db.execute(select(Matter).where(Matter.id == matter_id))
    matter = matter_result.scalar_one_or_none()
    if matter is None:
        raise ValueError(f"Matter {matter_id} not found")

    check_rate_limit(firm_id=matter.firm_id, matter_id=matter.id)

    # Gather documents with extracted data
    docs_result = await db.execute(
        select(Document).where(
            Document.matter_id == matter_id,
            Document.ai_extracted_data.isnot(None),
        )
    )
    docs = list(docs_result.scalars().all())

    documents_data: list[dict[str, Any]] = []
    for doc in docs:
        extracted = doc.ai_extracted_data or {}
        # Skip docs that only have metadata/status fields
        meaningful_fields = {
            k: v for k, v in extracted.items()
            if not k.startswith("_") and k not in ("classification_status", "extraction_status", "reason")
            and v is not None
        }
        if meaningful_fields:
            documents_data.append({
                "id": str(doc.id),
                "filename": doc.filename,
                "doc_type": doc.doc_type or "unknown",
                "extracted_data": meaningful_fields,
            })

    # Gather assets
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
        }
        for a in assets
    ]

    # Gather tasks
    tasks_result = await db.execute(
        select(Task.title).where(Task.matter_id == matter_id)
    )
    existing_tasks = [row[0] for row in tasks_result.all()]

    # Gather stakeholders
    stakeholders_result = await db.execute(
        select(Stakeholder.full_name).where(Stakeholder.matter_id == matter_id)
    )
    stakeholder_names = [row[0] for row in stakeholders_result.all()]

    # If no documents have extracted data, return empty (nothing to compare)
    if not documents_data and not assets_summary:
        return AIAnomalyResponse(anomalies=[])

    # Build prompt
    user_prompt = _build_user_prompt(
        documents_data=documents_data,
        assets_summary=assets_summary,
        existing_tasks=existing_tasks,
        stakeholder_names=stakeholder_names,
    )

    # Call Claude
    try:
        parsed_result, input_tokens, output_tokens = _call_claude(user_prompt)
    except Exception as exc:
        await _log_ai_usage(
            db,
            firm_id=matter.firm_id,
            matter_id=matter.id,
            operation="detect_anomalies",
            input_tokens=0,
            output_tokens=0,
            cost_estimate=0.0,
            status="error",
            error_message=str(exc),
        )
        raise

    cost_estimate = _estimate_cost(input_tokens, output_tokens)

    # Parse anomalies
    raw_anomalies = parsed_result.get("anomalies", [])
    anomalies: list[Anomaly] = []
    for a in raw_anomalies:
        if "type" in a and "description" in a and "severity" in a:
            # Convert string UUIDs to UUID objects (Claude returns strings)
            doc_id = a.get("document_id")
            asset_id_val = a.get("asset_id")
            try:
                doc_uuid = UUID(doc_id) if doc_id else None
            except (ValueError, TypeError):
                doc_uuid = None
            try:
                asset_uuid = UUID(asset_id_val) if asset_id_val else None
            except (ValueError, TypeError):
                asset_uuid = None

            anomalies.append(
                Anomaly(
                    type=a["type"],
                    description=a["description"],
                    document_id=doc_uuid,
                    asset_id=asset_uuid,
                    severity=a["severity"],
                )
            )

    response = AIAnomalyResponse(anomalies=anomalies)

    await _log_ai_usage(
        db,
        firm_id=matter.firm_id,
        matter_id=matter.id,
        operation="detect_anomalies",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_estimate=cost_estimate,
        metadata={
            "anomaly_count": len(anomalies),
            "anomaly_types": list({a.type for a in anomalies}),
        },
    )

    await event_logger.log(
        db,
        matter_id=matter.id,
        actor_id=None,
        actor_type=ActorType.ai,
        entity_type="matter",
        entity_id=matter.id,
        action="anomalies_detected",
        metadata={
            "anomaly_count": len(anomalies),
            "model": _MODEL,
            "prompt_version": get_prompt_version("detect_anomalies"),
        },
    )

    logger.info(
        "anomalies_detected",
        extra={
            "matter_id": str(matter_id),
            "anomaly_count": len(anomalies),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    )

    return response
