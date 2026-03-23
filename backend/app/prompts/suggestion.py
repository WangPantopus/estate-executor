"""Task suggestion prompts — v2.

Changes from v1:
- Shortened system prompt
- Added instruction to limit suggestions to 5-10 most important
- Removed redundant phase listing (already in tool schema enum)
"""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """\
You are an estate administration advisor. Given an estate profile, suggest additional tasks \
beyond the standard checklist that are specific to THIS estate's unique assets, entities, and jurisdiction. \
Focus on actionable gaps — not generic tasks. Limit to 5-10 most important suggestions."""


def build_user_prompt(
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
    """Build user prompt with estate profile context."""
    assets = (
        "\n".join(
            f"  - {a['title']} ({a['type']}, {a.get('institution', 'N/A')}, {a.get('value', '?')})"
            for a in assets_summary
        )
        or "  (none)"
    )

    tasks = "\n".join(f"  - {t}" for t in existing_tasks[:50]) or "  (none)"

    entities = "\n".join(f"  - {e['name']} ({e['type']})" for e in entities_summary) or "  (none)"

    return f"""\
Estate: {decedent_name} | {estate_type} | {jurisdiction} | Phase: {phase}

Assets:
{assets}

Current Tasks:
{tasks}

Entities:
{entities}

Roles: {", ".join(stakeholder_roles) or "none"}
Documents: {", ".join(document_types) or "none"}

Suggest tasks NOT already listed that this estate needs. Explain why each is needed."""


def build_tool_schema() -> dict[str, Any]:
    """Task suggestion tool schema."""
    return {
        "name": "suggest_tasks",
        "description": "Suggest estate tasks based on profile",
        "input_schema": {
            "type": "object",
            "properties": {
                "suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Task title"},
                            "description": {
                                "type": "string",
                                "description": "What needs to be done",
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
                            },
                            "reasoning": {"type": "string", "description": "Why this is needed"},
                        },
                        "required": ["title", "description", "phase", "reasoning"],
                    },
                },
            },
            "required": ["suggestions"],
        },
    }
