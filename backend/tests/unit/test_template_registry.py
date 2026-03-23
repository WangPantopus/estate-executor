"""Unit tests for the template registry."""

from app.services.template_registry import template_registry


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
        """State templates are loaded for all 5 states."""
        expected_states = ["CA", "TX", "NY", "FL", "IL"]
        for state in expected_states:
            assert state in template_registry.loaded_states, f"Missing state {state}"

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
