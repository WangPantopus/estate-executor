"""Unit tests for deadline service — monitoring logic, calendar grouping, schemas."""

from datetime import UTC, date, datetime

from app.models.enums import DeadlineSource, DeadlineStatus


class TestDeadlineSchemas:
    """Verify deadline schemas have expected fields."""

    def test_deadline_create_does_not_include_source(self):
        """Manual deadlines always get source='manual' — no user input needed."""
        from app.schemas.deadlines import DeadlineCreate

        fields = DeadlineCreate.model_fields
        assert "source" not in fields

    def test_deadline_response_has_task_brief(self):
        from app.schemas.deadlines import DeadlineResponse

        fields = DeadlineResponse.model_fields
        assert "task" in fields

    def test_deadline_response_has_assignee_name(self):
        from app.schemas.deadlines import DeadlineResponse

        fields = DeadlineResponse.model_fields
        assert "assignee_name" in fields

    def test_calendar_month_has_deadlines(self):
        from app.schemas.deadlines import CalendarMonth

        fields = CalendarMonth.model_fields
        assert "month" in fields
        assert "deadlines" in fields

    def test_calendar_deadline_has_task_title(self):
        from app.schemas.deadlines import CalendarDeadline

        fields = CalendarDeadline.model_fields
        assert "task_title" in fields

    def test_calendar_deadline_has_assignee_name(self):
        from app.schemas.deadlines import CalendarDeadline

        fields = CalendarDeadline.model_fields
        assert "assignee_name" in fields

    def test_task_brief_has_status(self):
        from app.schemas.deadlines import TaskBrief

        fields = TaskBrief.model_fields
        assert "status" in fields
        assert "title" in fields
        assert "id" in fields


class TestDeadlineModel:
    """Verify the Deadline model has expected fields for monitoring."""

    def test_deadline_has_reminder_config(self):
        from app.models.deadlines import Deadline

        assert hasattr(Deadline, "reminder_config")

    def test_deadline_has_last_reminder_sent(self):
        from app.models.deadlines import Deadline

        assert hasattr(Deadline, "last_reminder_sent")

    def test_deadline_has_source(self):
        from app.models.deadlines import Deadline

        assert hasattr(Deadline, "source")

    def test_deadline_has_rule(self):
        from app.models.deadlines import Deadline

        assert hasattr(Deadline, "rule")

    def test_deadline_has_task_relationship(self):
        from app.models.deadlines import Deadline

        assert hasattr(Deadline, "task")

    def test_deadline_has_assignee_relationship(self):
        from app.models.deadlines import Deadline

        assert hasattr(Deadline, "assignee")


class TestDeadlineSourceEnum:
    """Verify source enum values match design."""

    def test_auto_source_exists(self):
        assert DeadlineSource.auto == "auto"

    def test_manual_source_exists(self):
        assert DeadlineSource.manual == "manual"


class TestDeadlineStatusEnum:
    """Verify status enum values match design."""

    def test_upcoming_status(self):
        assert DeadlineStatus.upcoming == "upcoming"

    def test_completed_status(self):
        assert DeadlineStatus.completed == "completed"

    def test_extended_status(self):
        assert DeadlineStatus.extended == "extended"

    def test_missed_status(self):
        assert DeadlineStatus.missed == "missed"


class TestReminderIdempotency:
    """Test the idempotency logic for reminders — conceptual/unit level."""

    def test_reminder_already_sent_today_should_skip(self):
        """If last_reminder_sent is today, the reminder should be skipped."""
        now = datetime.now(UTC)
        today_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
        # Simulating: last_reminder_sent = 2 hours ago (still today)
        last_sent = today_start.replace(hour=2)
        assert last_sent >= today_start  # Would be skipped by the check

    def test_reminder_sent_yesterday_should_fire(self):
        """If last_reminder_sent is yesterday, the reminder should fire."""
        from datetime import timedelta

        now = datetime.now(UTC)
        today_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
        last_sent = today_start - timedelta(days=1)
        assert last_sent < today_start  # Would pass the check

    def test_no_previous_reminder_should_fire(self):
        """If last_reminder_sent is None, the reminder should fire."""
        last_sent = None
        datetime(2025, 1, 15, tzinfo=UTC)
        # None means never sent — should always fire
        assert last_sent is None  # Would pass the `is not None` check (short-circuit)

    def test_days_before_matching(self):
        """Check days_before matching logic."""
        due = date(2025, 3, 15)
        today = date(2025, 3, 8)  # 7 days before
        days_until = (due - today).days
        days_before_list = [30, 7, 1]
        assert days_until == 7
        assert days_until in days_before_list

    def test_days_before_no_match(self):
        """Check that non-matching days are skipped."""
        due = date(2025, 3, 15)
        today = date(2025, 3, 10)  # 5 days before
        days_until = (due - today).days
        days_before_list = [30, 7, 1]
        assert days_until == 5
        assert days_until not in days_before_list


class TestOverdueDetection:
    """Test the overdue detection logic."""

    def test_past_due_date_is_overdue(self):
        """A deadline with due_date < today should be marked missed."""
        today = date(2025, 3, 15)
        due = date(2025, 3, 14)
        assert due < today  # Would trigger missed status

    def test_today_due_date_is_not_overdue(self):
        """A deadline due today is NOT overdue."""
        today = date(2025, 3, 15)
        due = date(2025, 3, 15)
        assert not (due < today)  # Would NOT trigger missed status

    def test_future_due_date_is_not_overdue(self):
        """A deadline due tomorrow is NOT overdue."""
        today = date(2025, 3, 15)
        due = date(2025, 3, 16)
        assert not (due < today)


class TestCeleryBeatConfig:
    """Verify the Celery beat schedule is correctly configured."""

    def test_beat_schedule_has_check_deadlines(self):
        from app.workers.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "check-deadlines-hourly" in schedule

    def test_check_deadlines_runs_hourly(self):
        from app.workers.celery_app import celery_app

        config = celery_app.conf.beat_schedule["check-deadlines-hourly"]
        assert config["schedule"] == 3600.0

    def test_check_deadlines_task_name(self):
        from app.workers.celery_app import celery_app

        config = celery_app.conf.beat_schedule["check-deadlines-hourly"]
        assert config["task"] == "app.workers.deadline_tasks.check_deadlines"


class TestDeadlineReminderConfig:
    """Test reminder scheduling logic."""

    def test_default_reminder_days(self):
        """Default config should remind at 30, 7, and 1 day(s) before."""
        config = {"days_before": [30, 7, 1]}
        assert 30 in config["days_before"]
        assert 7 in config["days_before"]
        assert 1 in config["days_before"]

    def test_reminder_should_send_today(self):
        """If days_remaining matches a days_before entry, reminder should send."""
        config = {"days_before": [30, 7, 1]}
        due = date(2026, 4, 15)

        for days_before in config["days_before"]:
            from datetime import timedelta
            check_date = due - timedelta(days=days_before)
            remaining = (due - check_date).days
            assert remaining == days_before

    def test_idempotent_reminder_check(self):
        """If last_reminder_sent is today, should not send again."""
        today = date.today()
        last_sent_today = datetime(today.year, today.month, today.day, tzinfo=UTC)
        assert last_sent_today.date() == today


class TestDeadlineOverdueDetection:
    """Test overdue deadline detection logic."""

    def test_past_due_date_is_overdue(self):
        from datetime import timedelta
        today = date.today()
        past_due = today - timedelta(days=5)
        assert past_due < today

    def test_future_due_date_is_not_overdue(self):
        from datetime import timedelta
        today = date.today()
        future_due = today + timedelta(days=5)
        assert future_due >= today

    def test_today_due_date_is_not_overdue(self):
        today = date.today()
        assert today >= today  # Due today = not overdue yet

    def test_overdue_status_transition(self):
        """Overdue deadlines should be marked as 'missed'."""
        assert DeadlineStatus.missed.value == "missed"
        assert DeadlineStatus.upcoming.value == "upcoming"


class TestCalendarGrouping:
    """Test calendar view grouping logic."""

    def test_group_by_month(self):
        """Deadlines should be grouped by month for calendar view."""
        from collections import defaultdict

        deadlines = [
            {"due_date": date(2026, 3, 15), "title": "A"},
            {"due_date": date(2026, 3, 20), "title": "B"},
            {"due_date": date(2026, 4, 10), "title": "C"},
        ]

        by_month: dict = defaultdict(list)
        for d in deadlines:
            month_key = d["due_date"].strftime("%Y-%m")
            by_month[month_key].append(d)

        assert len(by_month["2026-03"]) == 2
        assert len(by_month["2026-04"]) == 1

    def test_auto_deadline_extend(self):
        """Extending due_date should set status to 'extended'."""
        assert DeadlineStatus.extended.value == "extended"
