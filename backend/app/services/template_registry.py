"""Task template registry — loads YAML templates and provides merged template sets."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Root directory for template YAML files
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Estate type YAML filenames (without extension) — must match EstateType enum values
_ESTATE_TYPE_FILES = [
    "testate_probate",
    "intestate_probate",
    "trust_administration",
    "conservatorship",
    "mixed_probate_trust",
]


class TemplateRegistry:
    """Singleton registry that loads and serves task templates from YAML files.

    Templates are loaded once at import time. The registry merges base templates
    with estate-type-specific and state-specific templates, filtering by conditions.
    """

    def __init__(self) -> None:
        self._base_templates: list[dict[str, Any]] = []
        self._estate_type_templates: dict[str, list[dict[str, Any]]] = {}
        self._state_templates: dict[str, list[dict[str, Any]]] = {}
        self._state_deadlines: dict[str, list[dict[str, Any]]] = {}
        self._load_all()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_yaml(self, path: Path) -> Any:
        """Load and parse a single YAML file."""
        if not path.exists():
            logger.warning("Template file not found: %s", path)
            return None
        with open(path) as f:
            return yaml.safe_load(f)

    def _load_all(self) -> None:
        """Load all template YAML files from the templates directory."""
        # Base tasks (common to all estate types)
        base_path = _TEMPLATES_DIR / "base_tasks.yaml"
        data = self._load_yaml(base_path)
        if isinstance(data, list):
            self._base_templates = data
            logger.info("Loaded %d base templates", len(data))

        # Estate-type-specific templates
        for estate_type in _ESTATE_TYPE_FILES:
            path = _TEMPLATES_DIR / f"{estate_type}.yaml"
            data = self._load_yaml(path)
            if isinstance(data, list):
                self._estate_type_templates[estate_type] = data
                logger.info("Loaded %d templates for %s", len(data), estate_type)

        # State-specific templates and deadlines
        states_dir = _TEMPLATES_DIR / "states"
        if states_dir.is_dir():
            for yaml_file in sorted(states_dir.glob("*.yaml")):
                state_code = yaml_file.stem.upper()
                data = self._load_yaml(yaml_file)
                if isinstance(data, dict):
                    tasks = data.get("tasks", [])
                    deadlines = data.get("deadlines", [])
                    if tasks:
                        self._state_templates[state_code] = tasks
                    if deadlines:
                        self._state_deadlines[state_code] = deadlines
                    logger.info(
                        "Loaded %d tasks + %d deadlines for state %s",
                        len(tasks),
                        len(deadlines),
                        state_code,
                    )

    # ------------------------------------------------------------------
    # Condition evaluation
    # ------------------------------------------------------------------

    @staticmethod
    def _matches_conditions(
        template: dict[str, Any],
        estate_type: str,
        state: str,
        flags: list[str] | None = None,
    ) -> bool:
        """Check if a template's conditions match the current context.

        Rules:
        - conditions is None or missing → always include
        - conditions.estate_types set → include only if estate_type is in list
        - conditions.states set → include only if state is in list
        - conditions.flags set → include only if ALL flags are present
        """
        conditions = template.get("conditions")
        if not conditions:
            return True

        estate_types = conditions.get("estate_types")
        if estate_types and estate_type not in estate_types:
            return False

        states = conditions.get("states")
        if states and state not in states:
            return False

        required_flags = conditions.get("flags")
        if required_flags:
            current_flags = set(flags or [])
            if not all(f in current_flags for f in required_flags):
                return False

        return True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_templates(
        self,
        estate_type: str,
        state: str,
        flags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return merged, deduplicated, condition-filtered templates.

        Merge order: base → estate_type-specific → state-specific.
        Later entries with the same key override earlier ones.
        """
        seen_keys: set[str] = set()
        result: list[dict[str, Any]] = []

        # Collect all candidate templates in order
        candidates: list[dict[str, Any]] = []
        candidates.extend(self._base_templates)
        candidates.extend(self._estate_type_templates.get(estate_type, []))
        candidates.extend(self._state_templates.get(state, []))

        for tmpl in candidates:
            key = tmpl.get("key", "")
            if not key:
                continue
            if not self._matches_conditions(tmpl, estate_type, state, flags):
                continue
            if key in seen_keys:
                # Replace earlier entry with later one (state overrides estate_type)
                result = [t for t in result if t.get("key") != key]
            seen_keys.add(key)
            result.append(tmpl)

        return result

    def get_state_deadlines(
        self,
        state: str,
        estate_type: str,
    ) -> list[dict[str, Any]]:
        """Return state-specific deadline rules filtered by estate_type."""
        deadlines = self._state_deadlines.get(state, [])
        result = []
        for dl in deadlines:
            conditions = dl.get("conditions")
            if conditions:
                estate_types = conditions.get("estate_types", [])
                if estate_types and estate_type not in estate_types:
                    continue
            result.append(dl)
        return result

    @property
    def loaded_estate_types(self) -> list[str]:
        """Return list of estate types with loaded templates."""
        return list(self._estate_type_templates.keys())

    @property
    def loaded_states(self) -> list[str]:
        """Return list of states with loaded templates."""
        return sorted(set(list(self._state_templates.keys()) + list(self._state_deadlines.keys())))

    def get_state_coverage(self, state: str) -> dict[str, Any]:
        """Return coverage info for a single state (task count, deadline count, etc.)."""
        tasks = self._state_templates.get(state, [])
        deadlines = self._state_deadlines.get(state, [])
        return {
            "supported": state in set(self.loaded_states),
            "task_count": len(tasks),
            "deadline_count": len(deadlines),
            "has_tasks": bool(tasks),
            "has_deadlines": bool(deadlines),
        }


# All 50 US states + DC — canonical list used by the coverage API and tests.
ALL_JURISDICTIONS = [
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "DC",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
]

# Module-level singleton (loaded once at import time)
template_registry = TemplateRegistry()
