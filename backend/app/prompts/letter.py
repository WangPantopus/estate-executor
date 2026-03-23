"""Letter drafting prompts — v2.

Changes from v1:
- Shortened system prompt (removed redundant PII instructions)
- Compressed requirements list in user prompt
- Added instruction for handling missing context gracefully
"""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """\
Draft a formal estate administration letter. Use professional legal tone. \
NEVER include full SSN or account numbers — only masked versions (e.g., ****1234). \
If context is incomplete, write a reasonable letter with available information."""


def build_user_prompt(
    *,
    letter_label: str,
    letter_purpose: str,
    decedent_name: str,
    date_of_death: str | None,
    estate_type: str,
    jurisdiction: str,
    executor_name: str | None,
    executor_title: str,
    institution: str | None,
    account_number_masked: str | None,
    asset_title: str | None,
    asset_type: str | None,
    asset_value: str | None,
    court_case_number: str | None,
) -> str:
    """Build user prompt for letter drafting."""
    lines: list[str] = [
        f"Letter: {letter_label}",
        f"Purpose: {letter_purpose}",
        f"Decedent: {decedent_name}",
    ]
    if date_of_death:
        lines.append(f"Date of death: {date_of_death}")
    lines.append(f"Estate: {estate_type}, {jurisdiction}")
    if executor_name:
        lines.append(f"{executor_title}: {executor_name}")
    if court_case_number:
        lines.append(f"Case: {court_case_number}")
    if institution:
        lines.append(f"Institution: {institution}")
    if asset_title:
        lines.append(f"Asset: {asset_title} ({asset_type or 'unknown'})")
    if account_number_masked:
        lines.append(f"Account: {account_number_masked}")
    if asset_value:
        lines.append(f"Value: {asset_value}")

    context = "\n".join(lines)

    return f"""\
Draft a formal {letter_label.lower()} with subject line, salutation, body, and closing.

{context}

Include the {executor_title}'s authority. Reference decedent and date of death. 1-2 pages max."""


def build_tool_schema() -> dict[str, Any]:
    """Letter drafting tool schema."""
    return {
        "name": "draft_letter",
        "description": "Generate a formal estate letter",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Subject line"},
                "body": {"type": "string", "description": "Full letter body with salutation and closing"},
                "recipient_institution": {"type": "string", "description": "Recipient name"},
            },
            "required": ["subject", "body", "recipient_institution"],
        },
    }
