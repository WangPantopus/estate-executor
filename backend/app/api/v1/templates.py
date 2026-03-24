"""Template coverage API — exposes available state templates and coverage info."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.template_registry import template_registry

router = APIRouter()


@router.get("/coverage")
async def get_template_coverage() -> dict:
    """Return which states have template coverage and summary stats.

    This is a lightweight, unauthenticated endpoint that returns
    metadata about jurisdiction coverage. No sensitive data is exposed.
    """
    loaded = template_registry.loaded_states
    loaded_set = set(loaded)

    all_states = [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
        "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
        "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
        "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
        "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI",
        "WY",
    ]

    coverage = {}
    for state in all_states:
        has_tasks = bool(template_registry._state_templates.get(state))
        has_deadlines = bool(template_registry._state_deadlines.get(state))
        task_count = len(template_registry._state_templates.get(state, []))
        deadline_count = len(template_registry._state_deadlines.get(state, []))
        coverage[state] = {
            "supported": state in loaded_set,
            "task_count": task_count,
            "deadline_count": deadline_count,
            "has_tasks": has_tasks,
            "has_deadlines": has_deadlines,
        }

    return {
        "total_states": len(all_states),
        "covered_states": len(loaded),
        "coverage_percentage": round(len(loaded) / len(all_states) * 100, 1),
        "states": coverage,
    }
