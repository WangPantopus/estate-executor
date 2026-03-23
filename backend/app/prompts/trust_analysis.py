"""Trust analysis prompts — v2.

Changes from v1:
- Shortened system prompt
- Added instruction for partial trust documents
"""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """\
Analyze a trust document against the asset registry. Identify:
1. Which existing assets should be funded into this trust
2. Assets/accounts referenced in the trust but NOT in the registry

Reference assets by title. If trust provisions are unclear, note the ambiguity."""


def build_user_prompt(
    *,
    trust_data: dict[str, Any],
    assets_summary: list[dict[str, Any]],
) -> str:
    """Build user prompt for trust funding analysis."""
    trust_lines = "\n".join(
        f"  {k}: {v}" for k, v in trust_data.items()
        if v is not None and not str(k).startswith("_")
    ) or "  (no extracted fields)"

    assets = "\n".join(
        f"  [{a['id'][:8]}] {a['title']} ({a['type']}, {a.get('institution', 'N/A')}, transfer: {a.get('transfer_mechanism', '?')})"
        for a in assets_summary
    ) or "  (none)"

    return f"""\
Trust Details:
{trust_lines}

Asset Registry:
{assets}

Which assets should be funded into this trust? What referenced assets are missing from the registry?"""


def build_tool_schema() -> dict[str, Any]:
    """Trust analysis tool schema."""
    return {
        "name": "analyze_trust_funding",
        "description": "Analyze trust funding needs",
        "input_schema": {
            "type": "object",
            "properties": {
                "funding_suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "asset_id": {"type": "string"},
                            "asset_title": {"type": "string"},
                            "reasoning": {"type": "string"},
                        },
                        "required": ["asset_id", "asset_title", "reasoning"],
                    },
                },
                "missing_assets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "source_reference": {"type": "string"},
                        },
                        "required": ["description", "source_reference"],
                    },
                },
            },
            "required": ["funding_suggestions", "missing_assets"],
        },
    }
