"""Prompt registry — versioned, documented prompts for all AI operations.

Each prompt has a version string stored alongside AI results for traceability.
When prompts are updated, bump the version so we can correlate accuracy changes.
"""

from __future__ import annotations

# Current prompt versions — bump when prompt text changes
PROMPT_VERSIONS: dict[str, str] = {
    "classify": "classify-v2",
    "extract": "extract-v2",
    "draft_letter": "letter-v2",
    "suggest_tasks": "suggest-v2",
    "detect_anomalies": "anomaly-v2",
    "trust_analysis": "trust-v2",
}


def get_prompt_version(operation: str) -> str:
    """Get the current prompt version for an operation."""
    return PROMPT_VERSIONS.get(operation, f"{operation}-v1")
