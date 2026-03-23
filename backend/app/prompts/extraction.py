"""Extraction prompts — v2.

Changes from v1:
- Consolidated system prompt to be shorter
- Added explicit instruction for partial/poor-quality documents
- Reduced redundancy in null-field instructions
- Tightened field descriptions for token savings
"""

from __future__ import annotations

from typing import Any

# Per-type extraction schemas (unchanged data, referenced from here)
from app.services.ai_extraction_service import EXTRACTION_SCHEMAS


def build_system_prompt(doc_type: str) -> str:
    """Build system prompt for extraction."""
    display = doc_type.replace("_", " ")
    return (
        f"Extract structured data from this {display} for estate administration. "
        f"Return null for any field not clearly present. Never guess or hallucinate values. "
        f"For poor-quality scans, extract what you can and set unclear fields to null."
    )


def build_user_prompt(extracted_text: str, doc_type: str) -> str:
    """Build user prompt for extraction."""
    schema = EXTRACTION_SCHEMAS[doc_type]
    field_list = "\n".join(
        f"- {name}: {spec['description']}"
        for name, spec in schema["properties"].items()
    )

    return f"""\
Extract these fields from the document:

{field_list}

<document_text>
{extracted_text}
</document_text>"""


def build_tool_schema(doc_type: str) -> dict[str, Any]:
    """Build extraction tool schema for a specific doc type."""
    schema = EXTRACTION_SCHEMAS[doc_type]
    nullable_props: dict[str, Any] = {}
    for field_name, field_spec in schema["properties"].items():
        prop = {**field_spec}
        # Append null instruction to description
        prop["description"] = field_spec["description"] + ". Null if not found."
        # Allow null for non-array, non-boolean types
        if "type" in field_spec and field_spec["type"] not in ("array", "boolean"):
            prop["type"] = [field_spec["type"], "null"]
        nullable_props[field_name] = prop

    return {
        "name": "extract_data",
        "description": f"Extract fields from {doc_type.replace('_', ' ')}",
        "input_schema": {
            "type": "object",
            "properties": {
                "extracted_fields": {
                    "type": "object",
                    "properties": nullable_props,
                    "required": schema["required"],
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Extraction quality confidence",
                },
            },
            "required": ["extracted_fields", "confidence"],
        },
    }
