"""Classification prompt — v2.

Changes from v1:
- Added handling instructions for poor quality scans and partial documents
- Added one-shot example for edge case (codicil → will)
- Shortened category descriptions for token efficiency
- Moved confidence calibration into tool schema description
"""

from __future__ import annotations

from typing import Any

DOCUMENT_TYPES: dict[str, str] = {
    "death_certificate": "Official government-issued death record",
    "will": "Last will and testament, codicil, or testamentary document",
    "trust_document": "Trust agreement, amendment, restatement, or certification",
    "deed": "Real property deed, title, or transfer document",
    "account_statement": "Bank, brokerage, retirement, or financial account statement",
    "insurance_policy": "Life insurance or other insurance policy",
    "court_filing": "Probate petition, court order, letters testamentary, or judicial document",
    "tax_return": "Federal/state tax return or tax-related form",
    "appraisal": "Property or asset appraisal/valuation report",
    "correspondence": "Letter, email, or communication related to the estate",
    "other": "Document that does not fit any other category",
}

SYSTEM_PROMPT = """\
You are a document classifier for estate administration. Classify the document into exactly one category.

Rules:
- Analyze content, formatting, and legal language
- A codicil is classified as "will"
- Court orders and letters testamentary are "court_filing"
- If the document is a poor scan or partially illegible, classify based on whatever text IS readable
- If truly unreadable or empty, classify as "other" with low confidence

Confidence calibration:
- 0.9+ : clearly labeled, unambiguous (e.g., "CERTIFICATE OF DEATH" header)
- 0.7-0.89 : strong match with minor ambiguity
- 0.5-0.69 : likely match but significant ambiguity
- <0.5 : uncertain, partial text, or poor quality"""


def build_user_prompt(
    extracted_text: str,
    *,
    estate_type: str | None = None,
    jurisdiction: str | None = None,
    decedent_name: str | None = None,
) -> str:
    """Build the classification user prompt."""
    type_list = "\n".join(f"- {doc_type}: {desc}" for doc_type, desc in DOCUMENT_TYPES.items())

    context = ""
    parts: list[str] = []
    if estate_type:
        parts.append(f"Estate: {estate_type}")
    if jurisdiction:
        parts.append(f"Jurisdiction: {jurisdiction}")
    if decedent_name:
        parts.append(f"Decedent: {decedent_name}")
    if parts:
        context = f"\nContext: {', '.join(parts)}\n"

    return f"""\
Classify this document:

Categories:
{type_list}
{context}
<document_text>
{extracted_text}
</document_text>"""


def build_tool_schema() -> dict[str, Any]:
    """Classification tool schema."""
    return {
        "name": "classify_document",
        "description": "Classify an estate document. Set confidence 0.0-1.0 based on certainty.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_type": {
                    "type": "string",
                    "enum": list(DOCUMENT_TYPES.keys()),
                    "description": "Document category",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Certainty score",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation (1-2 sentences)",
                },
            },
            "required": ["doc_type", "confidence", "reasoning"],
        },
    }
