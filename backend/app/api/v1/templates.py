"""Template coverage API — exposes available state templates and coverage info."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.template_registry import ALL_JURISDICTIONS, template_registry

router = APIRouter()


@router.get("/coverage")
async def get_template_coverage() -> dict:
    """Return which states have template coverage and summary stats.

    This is a lightweight, unauthenticated endpoint that returns
    metadata about jurisdiction coverage. No sensitive data is exposed.
    """
    loaded = template_registry.loaded_states
    total = len(ALL_JURISDICTIONS)

    coverage = {state: template_registry.get_state_coverage(state) for state in ALL_JURISDICTIONS}

    return {
        "total_states": total,
        "covered_states": len(loaded),
        "coverage_percentage": round(len(loaded) / total * 100, 1) if total else 0.0,
        "states": coverage,
    }
