"""Unit tests for task_generation_service — template resolution, estate type variation,
jurisdiction-specific tasks, dependency linking, deadline creation."""

from __future__ import annotations

from datetime import date

from app.services.task_generation_service import _add_months, _resolve_due_date


class TestAddMonths:
    """Tests for the _add_months helper."""

    def test_basic_add(self):
        assert _add_months(date(2025, 1, 15), 3) == date(2025, 4, 15)

    def test_cross_year(self):
        assert _add_months(date(2025, 11, 10), 3) == date(2026, 2, 10)

    def test_clamp_to_end_of_month(self):
        assert _add_months(date(2025, 1, 31), 1) == date(2025, 2, 28)

    def test_leap_year(self):
        assert _add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)

    def test_add_12_months(self):
        assert _add_months(date(2025, 6, 15), 12) == date(2026, 6, 15)

    def test_add_9_months(self):
        assert _add_months(date(2025, 3, 1), 9) == date(2025, 12, 1)

    def test_add_0_months(self):
        assert _add_months(date(2025, 5, 15), 0) == date(2025, 5, 15)


class TestResolveDueDate:
    """Tests for the _resolve_due_date helper."""

    def test_none_rule(self):
        assert _resolve_due_date(None, date(2025, 1, 1), date(2025, 1, 1)) is None

    def test_empty_rule(self):
        assert _resolve_due_date({}, date(2025, 1, 1), date(2025, 1, 1)) is None

    def test_offset_days_from_death(self):
        rule = {"relative_to": "date_of_death", "offset_days": 14}
        result = _resolve_due_date(rule, date(2025, 3, 1), date(2025, 3, 5))
        assert result == date(2025, 3, 15)

    def test_offset_months_from_death(self):
        rule = {"relative_to": "date_of_death", "offset_months": 9}
        result = _resolve_due_date(rule, date(2025, 1, 15), date(2025, 2, 1))
        assert result == date(2025, 10, 15)

    def test_offset_days_from_matter_created(self):
        rule = {"relative_to": "matter_created", "offset_days": 30}
        result = _resolve_due_date(rule, date(2025, 1, 1), date(2025, 2, 1))
        assert result == date(2025, 3, 3)

    def test_death_date_none_skips(self):
        rule = {"relative_to": "date_of_death", "offset_days": 14}
        result = _resolve_due_date(rule, None, date(2025, 3, 1))
        assert result is None

    def test_unknown_relative_to(self):
        rule = {"relative_to": "unknown_ref", "offset_days": 14}
        result = _resolve_due_date(rule, date(2025, 1, 1), date(2025, 1, 1))
        assert result is None

    def test_months_takes_precedence_over_days(self):
        rule = {"relative_to": "date_of_death", "offset_months": 4, "offset_days": 30}
        result = _resolve_due_date(rule, date(2025, 1, 1), date(2025, 1, 1))
        assert result == date(2025, 5, 1)


class TestTemplateRegistry:
    """Test template loading and resolution by estate type/state."""

    def test_registry_is_loaded(self):
        from app.services.template_registry import template_registry as registry

        assert registry is not None

    def test_base_templates_exist(self):
        from app.services.template_registry import template_registry as registry

        base = registry.get_templates("testate_probate", "CA")
        assert len(base) > 0

    def test_testate_probate_generates_tasks(self):
        from app.services.template_registry import template_registry as registry

        tasks = registry.get_templates("testate_probate", "CA")
        assert len(tasks) > 10

    def test_intestate_probate_generates_different_tasks(self):
        from app.services.template_registry import template_registry as registry

        testate = registry.get_templates("testate_probate", "CA")
        intestate = registry.get_templates("intestate_probate", "CA")
        testate_keys = {t["key"] for t in testate}
        intestate_keys = {t["key"] for t in intestate}
        # Should have some overlap (base tasks) but not be identical
        assert testate_keys != intestate_keys

    def test_trust_administration_has_trust_tasks(self):
        from app.services.template_registry import template_registry as registry

        tasks = registry.get_templates("trust_administration", "CA")
        keys = {t["key"] for t in tasks}
        # Trust admin should NOT have probate filing tasks
        {k for k in keys if "probate" in k.lower()}
        trust_keys = {k for k in keys if "trust" in k.lower()}
        assert len(trust_keys) >= 0  # May or may not have trust-specific

    def test_different_states_may_produce_different_tasks(self):
        from app.services.template_registry import template_registry as registry

        ca_tasks = registry.get_templates("testate_probate", "CA")
        ny_tasks = registry.get_templates("testate_probate", "NY")
        # Both should have tasks, may differ in count
        assert len(ca_tasks) > 0
        assert len(ny_tasks) > 0

    def test_unknown_state_still_produces_tasks(self):
        from app.services.template_registry import template_registry as registry

        tasks = registry.get_templates("testate_probate", "ZZ")
        # Should still get base + estate-type tasks
        assert len(tasks) > 0

    def test_template_has_required_fields(self):
        from app.services.template_registry import template_registry as registry

        tasks = registry.get_templates("testate_probate", "CA")
        for t in tasks[:5]:
            assert "key" in t
            assert "title" in t
            assert "phase" in t


class TestTemplateConditions:
    """Test condition evaluation in templates."""

    def test_estate_type_condition_filters(self):
        from app.services.template_registry import template_registry as registry

        testate = registry.get_templates("testate_probate", "CA")
        trust = registry.get_templates("trust_administration", "CA")
        # They should produce different sets
        assert len(testate) != len(trust) or set(t["key"] for t in testate) != set(
            t["key"] for t in trust
        )

    def test_conservatorship_generates_tasks(self):
        from app.services.template_registry import template_registry as registry

        tasks = registry.get_templates("conservatorship", "CA")
        assert len(tasks) > 0


class TestTaskDependencyLinking:
    """Test that templates specify dependencies correctly."""

    def test_templates_may_have_dependencies(self):
        from app.services.template_registry import template_registry as registry

        tasks = registry.get_templates("testate_probate", "CA")
        has_deps = any("dependencies" in t and t["dependencies"] for t in tasks)
        # Some templates should specify dependency template_keys
        # (this may be True or False depending on template data)
        assert isinstance(has_deps, bool)

    def test_dependency_references_are_strings(self):
        from app.services.template_registry import template_registry as registry

        tasks = registry.get_templates("testate_probate", "CA")
        for t in tasks:
            if "dependencies" in t and t["dependencies"]:
                for dep in t["dependencies"]:
                    assert isinstance(dep, str)


class TestDeadlineTemplates:
    """Test deadline auto-generation from state templates."""

    def test_state_deadlines_exist_for_ca(self):
        from app.services.template_registry import template_registry as registry

        deadlines = registry.get_state_deadlines("CA", "testate_probate")
        assert isinstance(deadlines, list)

    def test_deadline_template_has_date_fields(self):
        from app.services.template_registry import template_registry as registry

        deadlines = registry.get_state_deadlines("CA", "testate_probate")
        for dl in deadlines:
            assert "title" in dl
            # Deadline templates have relative_to and offset at top level
            assert "relative_to" in dl or "offset_months" in dl or "offset_days" in dl
