"""Unit tests for the template registry."""

from app.services.template_registry import ALL_JURISDICTIONS, template_registry


class TestTemplateRegistryLoading:
    """Tests that YAML files are loaded correctly."""

    def test_singleton_loaded(self):
        """The module-level singleton has templates loaded."""
        assert len(template_registry._base_templates) >= 20

    def test_estate_types_loaded(self):
        """All expected estate type templates are loaded."""
        expected = [
            "testate_probate",
            "intestate_probate",
            "trust_administration",
            "conservatorship",
            "mixed_probate_trust",
        ]
        for et in expected:
            assert et in template_registry._estate_type_templates, f"Missing {et}"
            assert len(template_registry._estate_type_templates[et]) > 0

    def test_states_loaded(self):
        """State templates are loaded for all 51 jurisdictions (50 states + DC)."""
        for state in ALL_JURISDICTIONS:
            assert state in template_registry.loaded_states, f"Missing state {state}"
        assert len(template_registry.loaded_states) == 51

    def test_base_templates_have_required_fields(self):
        """Every base template has the required fields."""
        required = {"key", "title", "phase", "priority"}
        for tmpl in template_registry._base_templates:
            for field in required:
                assert field in tmpl, f"Template '{tmpl.get('key')}' missing '{field}'"

    def test_all_template_keys_unique_within_file(self):
        """Template keys should be unique within each category."""
        keys = [t["key"] for t in template_registry._base_templates]
        assert len(keys) == len(set(keys)), "Duplicate keys in base templates"

        for et, templates in template_registry._estate_type_templates.items():
            keys = [t["key"] for t in templates]
            assert len(keys) == len(set(keys)), f"Duplicate keys in {et} templates"

    def test_all_state_templates_have_required_fields(self):
        """Every state template task should have required fields."""
        required = {"key", "title", "phase", "priority"}
        for state, templates in template_registry._state_templates.items():
            for tmpl in templates:
                for field in required:
                    assert field in tmpl, (
                        f"State {state} template '{tmpl.get('key')}' missing '{field}'"
                    )

    def test_all_state_template_keys_unique(self):
        """Template keys should be unique within each state."""
        for state, templates in template_registry._state_templates.items():
            keys = [t["key"] for t in templates]
            assert len(keys) == len(set(keys)), f"Duplicate keys in {state} templates"

    def test_all_state_deadline_keys_unique(self):
        """Deadline keys should be unique within each state."""
        for state, deadlines in template_registry._state_deadlines.items():
            keys = [d["key"] for d in deadlines]
            assert len(keys) == len(set(keys)), f"Duplicate deadline keys in {state}"

    def test_every_state_has_tasks_and_deadlines(self):
        """Every loaded state should have both tasks and deadlines."""
        for state in template_registry.loaded_states:
            assert state in template_registry._state_templates, (
                f"State {state} loaded but has no tasks"
            )
            assert len(template_registry._state_templates[state]) > 0, (
                f"State {state} has empty tasks list"
            )
            assert state in template_registry._state_deadlines, (
                f"State {state} loaded but has no deadlines"
            )
            assert len(template_registry._state_deadlines[state]) > 0, (
                f"State {state} has empty deadlines list"
            )

    def test_all_state_template_keys_globally_unique(self):
        """Template keys should be globally unique across ALL states."""
        all_keys: dict[str, str] = {}
        for state, templates in template_registry._state_templates.items():
            for tmpl in templates:
                key = tmpl["key"]
                assert key not in all_keys, (
                    f"Duplicate key '{key}' in {state} (also in {all_keys[key]})"
                )
                all_keys[key] = state

    def test_all_state_deadline_keys_globally_unique(self):
        """Deadline keys should be globally unique across ALL states."""
        all_keys: dict[str, str] = {}
        for state, deadlines in template_registry._state_deadlines.items():
            for dl in deadlines:
                key = dl["key"]
                assert key not in all_keys, (
                    f"Duplicate deadline key '{key}' in {state} (also in {all_keys[key]})"
                )
                all_keys[key] = state


class TestGetTemplates:
    """Tests for the get_templates method."""

    def test_testate_probate_ca_generates_35_plus(self):
        """CA testate_probate should return 35+ templates (base + testate + CA)."""
        templates = template_registry.get_templates("testate_probate", "CA")
        assert len(templates) >= 35, f"Expected 35+, got {len(templates)}"

    def test_trust_administration_no_probate_tasks(self):
        """Trust administration should NOT include probate-specific tasks."""
        templates = template_registry.get_templates("trust_administration", "CA")
        keys = {t["key"] for t in templates}
        # These are testate_probate-only tasks
        assert "petition_for_probate" not in keys
        assert "obtain_letters_testamentary" not in keys
        assert "file_will_with_court" not in keys

    def test_trust_administration_has_trust_tasks(self):
        """Trust administration should include trust-specific tasks."""
        templates = template_registry.get_templates("trust_administration", "CA")
        keys = {t["key"] for t in templates}
        assert "notify_trust_beneficiaries" in keys
        assert "review_trust_funding_status" in keys
        assert "terminate_trust" in keys

    def test_base_tasks_always_included(self):
        """Base tasks should appear regardless of estate type."""
        for et in ["testate_probate", "trust_administration", "conservatorship"]:
            templates = template_registry.get_templates(et, "CA")
            keys = {t["key"] for t in templates}
            assert "obtain_death_certificates" in keys
            assert "apply_for_ein" in keys

    def test_state_tasks_only_for_correct_state(self):
        """CA-specific tasks should only appear for CA, not TX."""
        ca_templates = template_registry.get_templates("testate_probate", "CA")
        tx_templates = template_registry.get_templates("testate_probate", "TX")

        ca_keys = {t["key"] for t in ca_templates}
        tx_keys = {t["key"] for t in tx_templates}

        assert "ca_file_petition_superior_court" in ca_keys
        assert "ca_file_petition_superior_court" not in tx_keys

        assert "tx_file_application_probate" in tx_keys
        assert "tx_file_application_probate" not in ca_keys

    def test_condition_filtering_estate_type(self):
        """Tasks with estate_type conditions should only appear for matching types."""
        trust_templates = template_registry.get_templates("trust_administration", "CA")
        trust_keys = {t["key"] for t in trust_templates}

        # ca_file_petition_superior_court has conditions.estate_types
        # that excludes trust_administration
        assert "ca_file_petition_superior_court" not in trust_keys

        # ca_trust_notification_120_days includes trust_administration
        assert "ca_trust_notification_120_days" in trust_keys

    def test_unknown_state_returns_base_plus_estate_type(self):
        """Unknown state should still return base + estate_type templates."""
        templates = template_registry.get_templates("testate_probate", "ZZ")
        # base(20) + testate(15) - 1 (Form 706 requires high_value_estate flag) = 34
        assert len(templates) >= 34

    def test_deduplication_by_key(self):
        """Templates should be deduplicated by key."""
        templates = template_registry.get_templates("testate_probate", "CA")
        keys = [t["key"] for t in templates]
        assert len(keys) == len(set(keys))

    def test_flags_condition_filtering(self):
        """Tasks with flag conditions should only appear when flags match."""
        # Form 706 requires 'high_value_estate' flag
        no_flags = template_registry.get_templates("testate_probate", "CA")
        with_flags = template_registry.get_templates(
            "testate_probate", "CA", flags=["high_value_estate"]
        )

        no_flag_keys = {t["key"] for t in no_flags}
        with_flag_keys = {t["key"] for t in with_flags}

        assert "file_federal_estate_tax_706" not in no_flag_keys
        assert "file_federal_estate_tax_706" in with_flag_keys


class TestGetStateDeadlines:
    """Tests for the get_state_deadlines method."""

    def test_ca_deadlines_exist(self):
        """California should have deadlines defined."""
        deadlines = template_registry.get_state_deadlines("CA", "testate_probate")
        assert len(deadlines) >= 2

    def test_deadline_has_required_fields(self):
        """Each deadline should have key, title, and date calculation fields."""
        deadlines = template_registry.get_state_deadlines("CA", "testate_probate")
        for dl in deadlines:
            assert "key" in dl
            assert "title" in dl
            assert "relative_to" in dl or "offset_months" in dl or "offset_days" in dl

    def test_deadline_estate_type_filtering(self):
        """Deadlines should be filtered by estate_type."""
        probate_dls = template_registry.get_state_deadlines("CA", "testate_probate")
        trust_dls = template_registry.get_state_deadlines("CA", "trust_administration")

        probate_keys = {dl["key"] for dl in probate_dls}
        trust_keys = {dl["key"] for dl in trust_dls}

        # Creditor claim period is probate-only
        assert "ca_creditor_claim_period" in probate_keys
        assert "ca_creditor_claim_period" not in trust_keys

        # Trust contest period is trust-only
        assert "ca_trust_contest_period" in trust_keys

    def test_all_state_deadlines_have_required_fields(self):
        """Every state deadline should have key, title, and date calc fields."""
        for state, deadlines in template_registry._state_deadlines.items():
            for dl in deadlines:
                assert "key" in dl, f"State {state} deadline missing 'key'"
                assert "title" in dl, f"State {state} deadline missing 'title'"
                has_date_calc = (
                    "offset_months" in dl or "offset_days" in dl
                )
                assert has_date_calc, (
                    f"State {state} deadline '{dl.get('key')}' missing date calculation"
                )

    def test_all_states_produce_templates_for_testate_probate(self):
        """Every state should generate templates when used with testate_probate."""
        for state in template_registry.loaded_states:
            templates = template_registry.get_templates("testate_probate", state)
            # Should always get at least base + estate-type templates
            assert len(templates) >= 20, (
                f"State {state} produced only {len(templates)} templates for testate_probate"
            )

    def test_estate_tax_states_have_tax_deadline(self):
        """States with estate/inheritance tax should include a tax deadline."""
        # States known to have estate or inheritance taxes
        tax_states = {
            "CT", "DC", "HI", "IL", "IA", "KY", "ME", "MD", "MA", "MN",
            "NE", "NJ", "NY", "OR", "PA", "RI", "VT", "WA",
        }
        for state in tax_states:
            deadlines = template_registry.get_state_deadlines(state, "testate_probate")
            deadline_keys = {dl["key"] for dl in deadlines}
            has_tax_deadline = any(
                "tax" in key or "inheritance" in key for key in deadline_keys
            )
            assert has_tax_deadline, (
                f"Tax state {state} missing a tax/inheritance deadline"
            )

    def test_community_property_states_have_community_task(self):
        """Community property states should have a community property identification task."""
        # All 9 community property states
        community_property_states = {"AZ", "CA", "ID", "LA", "NM", "NV", "TX", "WA", "WI"}
        for state in community_property_states:
            templates = template_registry.get_templates(
                "testate_probate", state, flags=["surviving_spouse"]
            )
            keys = {t["key"] for t in templates}
            has_cp_task = any(
                "community" in key or "marital" in key or "spousal" in key
                for key in keys
            )
            assert has_cp_task, (
                f"Community property state {state} missing community property task"
            )


class TestStateCoverage:
    """Tests for the coverage API data."""

    def test_get_state_coverage_returns_correct_structure(self):
        """get_state_coverage should return expected dict shape."""
        coverage = template_registry.get_state_coverage("CA")
        assert "supported" in coverage
        assert "task_count" in coverage
        assert "deadline_count" in coverage
        assert "has_tasks" in coverage
        assert "has_deadlines" in coverage
        assert coverage["supported"] is True
        assert coverage["task_count"] > 0
        assert coverage["deadline_count"] > 0

    def test_unsupported_state_coverage(self):
        """An unknown state should return unsupported with zero counts."""
        coverage = template_registry.get_state_coverage("ZZ")
        assert coverage["supported"] is False
        assert coverage["task_count"] == 0
        assert coverage["deadline_count"] == 0

    def test_all_jurisdictions_have_coverage(self):
        """Every jurisdiction in ALL_JURISDICTIONS should be supported."""
        for state in ALL_JURISDICTIONS:
            coverage = template_registry.get_state_coverage(state)
            assert coverage["supported"] is True, f"State {state} not supported"
            assert coverage["has_tasks"] is True, f"State {state} has no tasks"
            assert coverage["has_deadlines"] is True, f"State {state} has no deadlines"

    def test_all_jurisdictions_count(self):
        """ALL_JURISDICTIONS should have exactly 51 entries."""
        assert len(ALL_JURISDICTIONS) == 51
        assert len(set(ALL_JURISDICTIONS)) == 51  # no duplicates
