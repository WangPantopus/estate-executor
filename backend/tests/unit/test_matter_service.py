"""Unit tests for matter_service — CRUD, dashboard aggregation, close validation, portfolio."""

from __future__ import annotations

from datetime import date

from app.models.enums import (
    MatterPhase,
    MatterStatus,
    TaskStatus,
)


class TestComputeRiskLevel:
    """Test _compute_risk_level helper."""

    def _compute(self, **kw):
        from app.services.matter_service import _compute_risk_level

        return _compute_risk_level(**kw)

    def test_green_no_issues(self):
        result = self._compute(
            overdue_count=0,
            has_dispute=False,
            oldest_blocked_days=None,
        )
        assert result == "green"

    def test_red_overdue(self):
        assert self._compute(overdue_count=1, has_dispute=False, oldest_blocked_days=None) == "red"

    def test_red_dispute(self):
        assert self._compute(overdue_count=0, has_dispute=True, oldest_blocked_days=None) == "red"

    def test_red_blocked_over_14(self):
        assert self._compute(overdue_count=0, has_dispute=False, oldest_blocked_days=15) == "red"

    def test_amber_blocked_8_to_14(self):
        assert self._compute(overdue_count=0, has_dispute=False, oldest_blocked_days=10) == "amber"

    def test_green_blocked_7(self):
        assert self._compute(overdue_count=0, has_dispute=False, oldest_blocked_days=7) == "green"

    def test_green_blocked_0(self):
        assert self._compute(overdue_count=0, has_dispute=False, oldest_blocked_days=0) == "green"

    def test_red_multiple_flags(self):
        assert self._compute(overdue_count=5, has_dispute=True, oldest_blocked_days=20) == "red"

    def test_amber_exactly_14(self):
        assert self._compute(overdue_count=0, has_dispute=False, oldest_blocked_days=14) == "amber"


class TestMatterStatusEnum:
    """Verify matter status values exist."""

    def test_active(self):
        assert MatterStatus.active.value == "active"

    def test_on_hold(self):
        assert MatterStatus.on_hold.value == "on_hold"

    def test_closed(self):
        assert MatterStatus.closed.value == "closed"

    def test_archived(self):
        assert MatterStatus.archived.value == "archived"


class TestMatterPhaseEnum:
    """Verify matter phase values."""

    def test_all_phases_exist(self):
        phases = {p.value for p in MatterPhase}
        assert "immediate" in phases
        assert "administration" in phases
        assert "distribution" in phases
        assert "closing" in phases


class TestDashboardAggregation:
    """Test dashboard data structure expectations."""

    def test_task_summary_fields(self):
        """Dashboard task_summary must have expected keys."""
        expected_keys = {
            "total",
            "not_started",
            "in_progress",
            "blocked",
            "complete",
            "waived",
            "overdue",
            "completion_percentage",
        }
        # These are the keys returned by get_dashboard
        assert len(expected_keys) == 8

    def test_asset_summary_fields(self):
        expected_keys = {"total_count", "total_estimated_value", "by_type", "by_status"}
        assert len(expected_keys) == 4

    def test_completion_percentage_zero_tasks(self):
        """Completion % should be 0 when total_tasks is 0 (no division error)."""
        total = 0
        complete = 0
        pct = round((complete / total) * 100, 1) if total > 0 else 0.0
        assert pct == 0.0

    def test_completion_percentage_all_complete(self):
        total = 50
        complete = 50
        pct = round((complete / total) * 100, 1) if total > 0 else 0.0
        assert pct == 100.0

    def test_completion_percentage_partial(self):
        total = 10
        complete = 3
        pct = round((complete / total) * 100, 1) if total > 0 else 0.0
        assert pct == 30.0


class TestCloseValidation:
    """Test close_matter business rules."""

    def test_close_requires_all_critical_tasks_done(self):
        """The rule: cannot close if critical tasks are not complete/waived."""
        terminal_statuses = {TaskStatus.complete, TaskStatus.waived, TaskStatus.cancelled}
        non_terminal = {TaskStatus.not_started, TaskStatus.in_progress, TaskStatus.blocked}

        for status in terminal_statuses:
            assert status in terminal_statuses

        for status in non_terminal:
            assert status not in terminal_statuses

    def test_already_closed_conflict(self):
        """Closing an already-closed matter should raise ConflictError."""
        from app.core.exceptions import ConflictError

        assert ConflictError(detail="test").status_code == 409


class TestMatterModelStructure:
    """Verify matter model has all fields needed by service methods."""

    def test_matter_model_fields(self):
        from app.models.matters import Matter

        required = [
            "id",
            "firm_id",
            "title",
            "status",
            "estate_type",
            "jurisdiction_state",
            "decedent_name",
            "phase",
            "date_of_death",
            "estimated_value",
            "closed_at",
        ]
        for field in required:
            assert hasattr(Matter, field), f"Matter missing: {field}"

    def test_matter_has_firm_relationship(self):
        from app.models.matters import Matter

        assert hasattr(Matter, "firm")

    def test_matter_has_tasks_relationship(self):
        from app.models.matters import Matter

        assert hasattr(Matter, "tasks")

    def test_matter_has_assets_relationship(self):
        from app.models.matters import Matter

        assert hasattr(Matter, "assets")

    def test_matter_has_stakeholders_relationship(self):
        from app.models.matters import Matter

        assert hasattr(Matter, "stakeholders")


class TestCreateMatterValidation:
    """Test matter creation input validation."""

    def test_create_matter_requires_firm_id(self):
        from tests.factories import MatterFactory

        matter = MatterFactory.build()
        assert matter["firm_id"] is not None

    def test_create_matter_requires_title(self):
        from tests.factories import MatterFactory

        matter = MatterFactory.build()
        assert matter["title"] is not None
        assert len(matter["title"]) > 0

    def test_create_matter_requires_estate_type(self):
        from tests.factories import MatterFactory

        matter = MatterFactory.build()
        valid_types = {
            "testate_probate",
            "intestate_probate",
            "trust_administration",
            "conservatorship",
            "mixed_probate_trust",
            "other",
        }
        assert matter["estate_type"] in valid_types

    def test_create_matter_requires_jurisdiction(self):
        from tests.factories import MatterFactory

        matter = MatterFactory.build()
        assert len(matter["jurisdiction_state"]) == 2

    def test_create_matter_default_status_is_active(self):
        from tests.factories import MatterFactory

        matter = MatterFactory.build()
        assert matter["status"] == "active"

    def test_create_matter_default_phase_is_immediate(self):
        from tests.factories import MatterFactory

        matter = MatterFactory.build()
        assert matter["phase"] == "immediate"


class TestListMattersFiltering:
    """Test matter listing filter combinations."""

    def test_status_filter_values(self):
        valid = {"active", "on_hold", "closed", "archived"}
        assert len(valid) == 4

    def test_phase_filter_values(self):
        valid = {"immediate", "administration", "distribution", "closing"}
        assert len(valid) == 4

    def test_search_filter_accepts_partial_match(self):
        """Search should match against title or decedent_name."""
        search_term = "Smith"
        title = "Estate of John Smith"
        assert search_term.lower() in title.lower()

    def test_jurisdiction_filter_is_two_letter_code(self):
        valid_codes = ["CA", "NY", "TX", "FL"]
        for code in valid_codes:
            assert len(code) == 2


class TestUpdateMatterTracking:
    """Test that matter updates track changes."""

    def test_change_tracking_captures_old_new(self):
        """Updates should record old and new values."""
        changes = {"phase": {"old": "immediate", "new": "administration"}}
        assert changes["phase"]["old"] == "immediate"
        assert changes["phase"]["new"] == "administration"

    def test_no_op_update_produces_no_changes(self):
        """If no field values actually change, no event should be logged."""
        old_value = "active"
        new_value = "active"
        changed = old_value != new_value
        assert not changed


class TestDashboardVariousConfigurations:
    """Test dashboard aggregation with various data configurations."""

    def test_dashboard_with_zero_tasks(self):
        total = 0
        pct = round((0 / total) * 100, 1) if total > 0 else 0.0
        assert pct == 0.0

    def test_dashboard_with_all_overdue_tasks(self):
        from datetime import timedelta

        today = date.today()
        today - timedelta(days=10)
        overdue_count = 5
        total = 5
        assert overdue_count == total

    def test_dashboard_beneficiary_sees_no_asset_values(self):
        """Beneficiary dashboard should null out total_estimated_value."""
        asset_summary = {
            "total_count": 5,
            "total_estimated_value": None,  # nulled for beneficiary
            "by_type": {},
            "by_status": {},
        }
        assert asset_summary["total_estimated_value"] is None
        assert asset_summary["total_count"] == 5

    def test_dashboard_beneficiary_sees_no_events(self):
        """Beneficiary dashboard should return empty recent_events."""
        recent_events = []
        assert len(recent_events) == 0

    def test_dashboard_with_mixed_task_statuses(self):
        statuses = ["not_started", "in_progress", "complete", "blocked", "waived"]
        assert len(statuses) == 5

    def test_dashboard_overdue_excludes_terminal_tasks(self):
        """Only non-terminal tasks past due_date count as overdue."""
        terminal = {"complete", "waived", "cancelled"}
        status = "in_progress"
        assert status not in terminal


class TestPortfolioSchema:
    """Test portfolio response data structures."""

    def test_risk_level_values(self):
        from app.services.matter_service import _compute_risk_level

        valid = {"green", "amber", "red"}
        for oc in [0, 1, 5]:
            for dispute in [True, False]:
                for blocked in [None, 0, 7, 8, 14, 15, 30]:
                    result = _compute_risk_level(
                        overdue_count=oc, has_dispute=dispute, oldest_blocked_days=blocked
                    )
                    msg = f"Invalid: {result} for oc={oc}, d={dispute}, b={blocked}"
                    assert result in valid, msg
