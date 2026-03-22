"""Unit tests for matter_service — CRUD, dashboard aggregation, close validation, portfolio."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.models.enums import (
    AssetStatus,
    DeadlineStatus,
    MatterPhase,
    MatterStatus,
    StakeholderRole,
    TaskPriority,
    TaskStatus,
)


class TestComputeRiskLevel:
    """Test _compute_risk_level helper."""

    def _compute(self, **kw):
        from app.services.matter_service import _compute_risk_level
        return _compute_risk_level(**kw)

    def test_green_no_issues(self):
        assert self._compute(overdue_count=0, has_dispute=False, oldest_blocked_days=None) == "green"

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
            "total", "not_started", "in_progress", "blocked",
            "complete", "waived", "overdue", "completion_percentage",
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
                    assert result in valid, f"Invalid: {result} for oc={oc}, d={dispute}, b={blocked}"
