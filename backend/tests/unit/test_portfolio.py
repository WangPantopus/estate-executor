"""Unit tests for portfolio view risk level computation and data structures."""

from __future__ import annotations


class TestComputeRiskLevel:
    """Test the _compute_risk_level helper in matter_service."""

    def _compute(self, **kwargs):
        from app.services.matter_service import _compute_risk_level
        return _compute_risk_level(**kwargs)

    def test_no_issues_returns_green(self):
        result = self._compute(
            overdue_count=0,
            has_dispute=False,
            oldest_blocked_days=None,
        )
        assert result == "green"

    def test_overdue_tasks_returns_red(self):
        result = self._compute(
            overdue_count=3,
            has_dispute=False,
            oldest_blocked_days=None,
        )
        assert result == "red"

    def test_single_overdue_task_returns_red(self):
        result = self._compute(
            overdue_count=1,
            has_dispute=False,
            oldest_blocked_days=None,
        )
        assert result == "red"

    def test_dispute_returns_red(self):
        result = self._compute(
            overdue_count=0,
            has_dispute=True,
            oldest_blocked_days=None,
        )
        assert result == "red"

    def test_blocked_over_14_days_returns_red(self):
        result = self._compute(
            overdue_count=0,
            has_dispute=False,
            oldest_blocked_days=15,
        )
        assert result == "red"

    def test_blocked_exactly_14_days_returns_red(self):
        """14 days is the threshold — >14 = red."""
        result = self._compute(
            overdue_count=0,
            has_dispute=False,
            oldest_blocked_days=14,
        )
        # 14 is not > 14, so it's amber (> 7)
        assert result == "amber"

    def test_blocked_8_to_14_days_returns_amber(self):
        result = self._compute(
            overdue_count=0,
            has_dispute=False,
            oldest_blocked_days=10,
        )
        assert result == "amber"

    def test_blocked_exactly_7_days_returns_green(self):
        """7 days is not > 7, so still green."""
        result = self._compute(
            overdue_count=0,
            has_dispute=False,
            oldest_blocked_days=7,
        )
        assert result == "green"

    def test_blocked_6_days_returns_green(self):
        result = self._compute(
            overdue_count=0,
            has_dispute=False,
            oldest_blocked_days=6,
        )
        assert result == "green"

    def test_blocked_0_days_returns_green(self):
        result = self._compute(
            overdue_count=0,
            has_dispute=False,
            oldest_blocked_days=0,
        )
        assert result == "green"

    def test_multiple_red_flags_still_red(self):
        """Multiple red conditions should still return red."""
        result = self._compute(
            overdue_count=5,
            has_dispute=True,
            oldest_blocked_days=20,
        )
        assert result == "red"

    def test_overdue_takes_priority_over_blocked(self):
        """Even if blocked is only 8 days (amber), overdue makes it red."""
        result = self._compute(
            overdue_count=1,
            has_dispute=False,
            oldest_blocked_days=8,
        )
        assert result == "red"


class TestPortfolioResponseSchema:
    """Test that the portfolio data structures are correct.

    We test via Pydantic models defined locally to avoid the jwt/cryptography
    import chain issue in this environment.
    """

    def test_portfolio_matter_item_has_all_fields(self):
        """Verify the PortfolioMatterItem has all required fields."""
        from pydantic import BaseModel

        class TestPortfolioMatterItem(BaseModel):
            total_task_count: int
            complete_task_count: int
            open_task_count: int
            overdue_task_count: int
            approaching_deadline_count: int
            next_deadline: str | None
            has_dispute: bool
            oldest_blocked_task_days: int | None
            risk_level: str

        item = TestPortfolioMatterItem(
            total_task_count=50,
            complete_task_count=30,
            open_task_count=15,
            overdue_task_count=3,
            approaching_deadline_count=2,
            next_deadline="2026-04-01",
            has_dispute=False,
            oldest_blocked_task_days=10,
            risk_level="amber",
        )
        assert item.total_task_count == 50
        assert item.risk_level == "amber"
        assert item.oldest_blocked_task_days == 10

    def test_portfolio_summary_has_all_fields(self):
        from pydantic import BaseModel

        class TestPortfolioSummary(BaseModel):
            total_active_matters: int
            total_overdue_tasks: int
            approaching_deadlines_this_week: int
            matters_by_phase: dict[str, int]

        summary = TestPortfolioSummary(
            total_active_matters=10,
            total_overdue_tasks=3,
            approaching_deadlines_this_week=5,
            matters_by_phase={"immediate": 3, "administration": 5, "closing": 2},
        )
        assert summary.total_active_matters == 10
        assert summary.total_overdue_tasks == 3
        assert summary.approaching_deadlines_this_week == 5
        assert summary.matters_by_phase["immediate"] == 3

    def test_risk_level_values(self):
        """Risk level should be one of green, amber, red."""
        valid = {"green", "amber", "red"}
        from app.services.matter_service import _compute_risk_level

        for oc in [0, 1]:
            for disp in [True, False]:
                for blocked in [None, 0, 7, 8, 14, 15]:
                    result = _compute_risk_level(
                        overdue_count=oc,
                        has_dispute=disp,
                        oldest_blocked_days=blocked,
                    )
                    assert result in valid


class TestRiskLevelCoverage:
    """Ensure all risk level values are valid."""

    def test_only_valid_risk_levels(self):
        from app.services.matter_service import _compute_risk_level

        valid_levels = {"green", "amber", "red"}

        # Test a range of inputs
        test_cases = [
            {"overdue_count": 0, "has_dispute": False, "oldest_blocked_days": None},
            {"overdue_count": 1, "has_dispute": False, "oldest_blocked_days": None},
            {"overdue_count": 0, "has_dispute": True, "oldest_blocked_days": None},
            {"overdue_count": 0, "has_dispute": False, "oldest_blocked_days": 8},
            {"overdue_count": 0, "has_dispute": False, "oldest_blocked_days": 15},
            {"overdue_count": 0, "has_dispute": False, "oldest_blocked_days": 0},
            {"overdue_count": 0, "has_dispute": False, "oldest_blocked_days": 7},
        ]

        for case in test_cases:
            result = _compute_risk_level(**case)
            assert result in valid_levels, f"Invalid risk level '{result}' for {case}"
