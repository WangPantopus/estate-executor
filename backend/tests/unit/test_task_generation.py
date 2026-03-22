"""Unit tests for task generation helpers (date calculation, etc.)."""

from datetime import date

from app.services.task_generation_service import _add_months, _resolve_due_date


class TestAddMonths:
    """Tests for the _add_months helper."""

    def test_basic_add(self):
        assert _add_months(date(2025, 1, 15), 3) == date(2025, 4, 15)

    def test_cross_year(self):
        assert _add_months(date(2025, 11, 10), 3) == date(2026, 2, 10)

    def test_clamp_to_end_of_month(self):
        """Adding 1 month to Jan 31 should give Feb 28 (non-leap year)."""
        assert _add_months(date(2025, 1, 31), 1) == date(2025, 2, 28)

    def test_leap_year(self):
        """Adding 1 month to Jan 31 in a leap year should give Feb 29."""
        assert _add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)

    def test_add_12_months(self):
        assert _add_months(date(2025, 6, 15), 12) == date(2026, 6, 15)

    def test_add_9_months(self):
        """9 months from date of death — common for Form 706."""
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
        """If date_of_death is None and rule references it, return None."""
        rule = {"relative_to": "date_of_death", "offset_days": 14}
        result = _resolve_due_date(rule, None, date(2025, 3, 1))
        assert result is None

    def test_unknown_relative_to(self):
        rule = {"relative_to": "unknown_ref", "offset_days": 14}
        result = _resolve_due_date(rule, date(2025, 1, 1), date(2025, 1, 1))
        assert result is None

    def test_months_takes_precedence_over_days(self):
        """When both offset_months and offset_days are set, months wins."""
        rule = {
            "relative_to": "date_of_death",
            "offset_months": 4,
            "offset_days": 30,
        }
        result = _resolve_due_date(rule, date(2025, 1, 1), date(2025, 1, 1))
        assert result == date(2025, 5, 1)  # 4 months, not 30 days
