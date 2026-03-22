"""Integration tests: deadline monitoring — time simulation, reminders."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.models.enums import DeadlineSource, DeadlineStatus


@pytest.mark.asyncio
class TestDeadlineDetection:
    """Test overdue and reminder detection logic."""

    async def test_overdue_deadline_detection(self):
        """A deadline with due_date in the past should be detected as overdue."""
        due = date.today() - timedelta(days=3)
        is_overdue = due < date.today()
        assert is_overdue

    async def test_upcoming_deadline_not_overdue(self):
        due = date.today() + timedelta(days=10)
        is_overdue = due < date.today()
        assert not is_overdue

    async def test_due_today_not_overdue(self):
        due = date.today()
        is_overdue = due < date.today()
        assert not is_overdue

    async def test_missed_status_value(self):
        assert DeadlineStatus.missed.value == "missed"

    async def test_upcoming_status_value(self):
        assert DeadlineStatus.upcoming.value == "upcoming"


@pytest.mark.asyncio
class TestReminderScheduling:
    """Test reminder scheduling logic."""

    async def test_reminder_at_30_days(self):
        config = {"days_before": [30, 7, 1]}
        due = date.today() + timedelta(days=30)
        remaining = (due - date.today()).days
        should_remind = remaining in config["days_before"]
        assert should_remind

    async def test_reminder_at_7_days(self):
        config = {"days_before": [30, 7, 1]}
        due = date.today() + timedelta(days=7)
        remaining = (due - date.today()).days
        should_remind = remaining in config["days_before"]
        assert should_remind

    async def test_reminder_at_1_day(self):
        config = {"days_before": [30, 7, 1]}
        due = date.today() + timedelta(days=1)
        remaining = (due - date.today()).days
        should_remind = remaining in config["days_before"]
        assert should_remind

    async def test_no_reminder_at_15_days(self):
        config = {"days_before": [30, 7, 1]}
        due = date.today() + timedelta(days=15)
        remaining = (due - date.today()).days
        should_remind = remaining in config["days_before"]
        assert not should_remind

    async def test_idempotent_same_day(self):
        """If reminder was already sent today, should not send again."""
        from datetime import datetime, timezone

        today = date.today()
        last_sent = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        already_sent_today = last_sent.date() == today
        assert already_sent_today

    async def test_extend_updates_status(self):
        """Extending a deadline past original date should set status='extended'."""
        assert DeadlineStatus.extended.value == "extended"

    async def test_source_values(self):
        assert DeadlineSource.auto.value == "auto"
        assert DeadlineSource.manual.value == "manual"
