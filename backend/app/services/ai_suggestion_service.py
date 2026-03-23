"""AI task suggestion service — suggests additional tasks based on estate profile.

Gathers matter context (assets, existing tasks, entities, jurisdiction) and
uses Claude to identify missing tasks beyond the standard checklist.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.core.config import settings
from app.core.events import event_logger
from app.models.ai_usage_logs import AIUsageLog
from app.models.assets import Asset
from app.models.documents import Document
from app.models.entities import Entity
from app.models.enums import ActorType
from app.models.matters import Matter
from app.models.stakeholders import Stakeholder
from app.models.tasks import Task
from app.prompts import get_prompt_version
from app.schemas.ai import AISuggestTasksResponse, TaskSuggestion
from app.services.ai_rate_limiter import check_rate_limit

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-20250514"
_INPUT_COST_PER_M = 3.0
_OUTPUT_COST_PER_M = 15.0

_SYSTEM_PROMPT = """You are an expert estate administration advisor. \
Given the profile of an estate (assets, existing tasks, entities, jurisdiction), \
identify additional tasks that may be needed beyond the standard checklist.

Focus on tasks that are specific to THIS estate's unique characteristics. \
Do not suggest generic tasks that would already be on a standard checklist. \
Instead, look for gaps based on the specific asset types, entity structures, \
and jurisdictional requirements present.

Valid task phases: immediate, asset_inventory, notification, probate_filing, \
tax, transfer_distribution, family_communication, closing, custom."""


def _build_user_prompt(
    *,
    decedent_name: str,
    estate_type: str,
    jurisdiction: str,
    phase: str,
    assets_summary: list[dict[str, Any]],
    existing_tasks: list[str],
    entities_summary: list[dict[str, str]],
    stakeholder_roles: list[str],
    document_types: list[str],
) -> str:
    """Build the user prompt with estate profile context."""
    asset_lines = (
        "\n".join(
            f"  - {a['title']} ({a['type']}, institution: {a.get('institution', 'N/A')}, value: {a.get('value', 'N/A')})"
            for a in assets_summary
        )
        or "  (no assets registered yet)"
    )

    task_lines = "\n".join(f"  - {t}" for t in existing_tasks) or "  (no tasks yet)"

    entity_lines = (
        "\n".join(f"  - {e['name']} ({e['type']})" for e in entities_summary) or "  (no entities)"
    )

    "\n".join(f"  - {d}" for d in document_types) or "  (no documents)"

    return f"""Analyze this estate profile and suggest additional tasks that may be needed:

Estate Profile:
  Decedent: {decedent_name}
  Estate type: {estate_type}
  Jurisdiction: {jurisdiction}
  Current phase: {phase}

Registered Assets:
{asset_lines}

Existing Tasks:
{task_lines}

Trust/Entity Structures:
{entity_lines}

Stakeholder Roles: {", ".join(stakeholder_roles) if stakeholder_roles else "None"}

Document Types on File: {", ".join(document_types) if document_types else "None"}

Based on this profile, suggest tasks that are NOT already in the existing task list \
but SHOULD be created given the specific assets, entities, and circumstances. \
Focus on actionable, specific tasks — not generic ones.

For each suggestion, explain WHY it's needed based on what you see in the profile."""


def _build_tool_schema() -> dict[str, Any]:
    """Build the tool-use schema for structured task suggestions."""
    return {
        "name": "suggest_tasks",
        "description": "Suggest additional estate administration tasks based on the estate profile",
        "input_schema": {
            "type": "object",
            "properties": {
                "suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Short, actionable task title",
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description of what needs to be done",
                            },
                            "phase": {
                                "type": "string",
                                "enum": [
                                    "immediate",
                                    "asset_inventory",
                                    "notification",
                                    "probate_filing",
                                    "tax",
                                    "transfer_distribution",
                                    "family_communication",
                                    "closing",
                                    "custom",
                                ],
                                "description": "Task phase in the estate administration workflow",
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Why this task is needed based on the estate profile",
                            },
                        },
                        "required": ["title", "description", "phase", "reasoning"],
                    },
                    "description": "List of suggested tasks",
                },
            },
            "required": ["suggestions"],
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
        tool_choice={"type": "tool", "name": "suggest_tasks"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    tool_result: dict[str, Any] | None = None
    for block in response.content:
        if block.type == "tool_use":
            tool_result = block.input  # type: ignore[assignment]
            break

    if tool_result is None:
        raise ValueError("Claude did not return a tool_use response for task suggestions")

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


async def suggest_tasks(
    db: AsyncSession,
    *,
    matter_id: UUID,
) -> AISuggestTasksResponse:
    """Suggest additional tasks based on the estate's asset profile.

    1. Gathers matter context, assets, tasks, entities, documents
    2. Calls Claude for task suggestions
    3. Logs usage and audit event
    """
    # Fetch matter
    matter_result = await db.execute(select(Matter).where(Matter.id == matter_id))
    matter = matter_result.scalar_one_or_none()
    if matter is None:
        raise ValueError(f"Matter {matter_id} not found")

    check_rate_limit(firm_id=matter.firm_id, matter_id=matter.id)

    # Gather assets
    assets_result = await db.execute(select(Asset).where(Asset.matter_id == matter_id))
    assets = list(assets_result.scalars().all())
    assets_summary = [
        {
            "title": a.title,
            "type": a.asset_type.value if hasattr(a.asset_type, "value") else str(a.asset_type),
            "institution": a.institution or "N/A",
            "value": f"${a.current_estimated_value:,.2f}"
            if a.current_estimated_value
            else "Unknown",
        }
        for a in assets
    ]

    # Gather existing tasks (titles only)
    tasks_result = await db.execute(select(Task.title).where(Task.matter_id == matter_id))
    existing_tasks = [row[0] for row in tasks_result.all()]

    # Gather entities
    entities_result = await db.execute(select(Entity).where(Entity.matter_id == matter_id))
    entities = list(entities_result.scalars().all())
    entities_summary = [
        {
            "name": e.name,
            "type": e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type),
        }
        for e in entities
    ]

    # Gather stakeholder roles
    stakeholders_result = await db.execute(
        select(Stakeholder.role).where(Stakeholder.matter_id == matter_id).distinct()
    )
    stakeholder_roles = [
        row[0].value if hasattr(row[0], "value") else str(row[0])
        for row in stakeholders_result.all()
    ]

    # Gather document types on file
    docs_result = await db.execute(
        select(Document.doc_type)
        .where(
            Document.matter_id == matter_id,
            Document.doc_type.isnot(None),
        )
        .distinct()
    )
    document_types = [row[0] for row in docs_result.all()]

    # Build prompt
    estate_type = (
        matter.estate_type.value.replace("_", " ").title()
        if hasattr(matter.estate_type, "value")
        else str(matter.estate_type)
    )
    phase = matter.phase.value if hasattr(matter.phase, "value") else str(matter.phase)

    user_prompt = _build_user_prompt(
        decedent_name=matter.decedent_name,
        estate_type=estate_type,
        jurisdiction=matter.jurisdiction_state,
        phase=phase,
        assets_summary=assets_summary,
        existing_tasks=existing_tasks,
        entities_summary=entities_summary,
        stakeholder_roles=stakeholder_roles,
        document_types=document_types,
    )

    # Call Claude
    try:
        parsed_result, input_tokens, output_tokens = _call_claude(user_prompt)
    except Exception as exc:
        await _log_ai_usage(
            db,
            firm_id=matter.firm_id,
            matter_id=matter.id,
            operation="suggest_tasks",
            input_tokens=0,
            output_tokens=0,
            cost_estimate=0.0,
            status="error",
            error_message=str(exc),
        )
        raise

    cost_estimate = _estimate_cost(input_tokens, output_tokens)

    # Parse suggestions
    raw_suggestions = parsed_result.get("suggestions", [])
    suggestions = [
        TaskSuggestion(
            title=s["title"],
            description=s["description"],
            phase=s["phase"],
            reasoning=s["reasoning"],
        )
        for s in raw_suggestions
        if all(k in s for k in ("title", "description", "phase", "reasoning"))
    ]

    response = AISuggestTasksResponse(suggestions=suggestions)

    await _log_ai_usage(
        db,
        firm_id=matter.firm_id,
        matter_id=matter.id,
        operation="suggest_tasks",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_estimate=cost_estimate,
        metadata={"suggestion_count": len(suggestions)},
    )

    await event_logger.log(
        db,
        matter_id=matter.id,
        actor_id=None,
        actor_type=ActorType.ai,
        entity_type="matter",
        entity_id=matter.id,
        action="tasks_suggested",
        metadata={
            "suggestion_count": len(suggestions),
            "model": _MODEL,
            "prompt_version": get_prompt_version("suggest_tasks"),
        },
    )

    logger.info(
        "tasks_suggested",
        extra={
            "matter_id": str(matter_id),
            "suggestion_count": len(suggestions),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    )

    return response
