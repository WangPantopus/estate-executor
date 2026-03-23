"""Anomaly detection prompts — v2.

Changes from v1:
- Compressed anomaly type descriptions
- Added >10% threshold guidance inline
- Shortened system prompt
"""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """\
You are an estate auditor. Compare document-extracted data against the asset registry, \
stakeholders, and tasks to find discrepancies.

Anomaly types:
- missing_asset: document mentions account/institution not in registry
- value_discrepancy: document value differs >10% from registered value
- missing_stakeholder: person named in document not in stakeholder list
- missing_task: asset exists but expected task is missing (e.g., insurance with no claim task)
- data_inconsistency: conflicting information between sources

Severity: high (immediate action), medium (review needed), low (informational). \
If no anomalies found, return empty list."""


def build_user_prompt(
    *,
    documents_data: list[dict[str, Any]],
    assets_summary: list[dict[str, Any]],
    existing_tasks: list[str],
    stakeholder_names: list[str],
) -> str:
    """Build user prompt for anomaly detection."""
    doc_lines: list[str] = []
    for d in documents_data:
        doc_lines.append(f"  [{d.get('id', '?')[:8]}] {d['filename']} ({d['doc_type']})")
        for field, value in d.get("extracted_data", {}).items():
            if value is not None:
                doc_lines.append(f"    {field}: {value}")
    doc_section = "\n".join(doc_lines) or "  (none)"

    assets = "\n".join(
        f"  [{a['id'][:8]}] {a['title']} ({a['type']}, {a.get('institution', 'N/A')}, {a.get('value', '?')})"
        for a in assets_summary
    ) or "  (none)"

    tasks = "\n".join(f"  - {t}" for t in existing_tasks[:50]) or "  (none)"

    return f"""\
Compare documents against registry. Report anomalies.

Documents:
{doc_section}

Assets:
{assets}

Tasks:
{tasks}

Stakeholders: {', '.join(stakeholder_names) or '(none)'}"""


def build_tool_schema() -> dict[str, Any]:
    """Anomaly detection tool schema."""
    return {
        "name": "report_anomalies",
        "description": "Report estate data anomalies",
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
                                "enum": ["missing_asset", "value_discrepancy", "missing_stakeholder", "missing_task", "data_inconsistency"],
                            },
                            "description": {"type": "string"},
                            "document_id": {"type": ["string", "null"]},
                            "asset_id": {"type": ["string", "null"]},
                            "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        },
                        "required": ["type", "description", "severity"],
                    },
                },
            },
            "required": ["anomalies"],
        },
    }
