"""Unit tests for time tracking — model, schemas, service signatures."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from app.models.time_entries import TimeEntry
from app.schemas.time_tracking import (
    TimeEntryCreate,
    TimeEntryListResponse,
    TimeEntryResponse,
    TimeEntryUpdate,
    TimeTrackingSummary,
)


class TestTimeEntryModel:
    """Verify TimeEntry model has expected fields."""

    def test_has_matter_id(self):
        assert hasattr(TimeEntry, "matter_id")

    def test_has_task_id(self):
        assert hasattr(TimeEntry, "task_id")

    def test_has_stakeholder_id(self):
        assert hasattr(TimeEntry, "stakeholder_id")

    def test_has_hours(self):
        assert hasattr(TimeEntry, "hours")

    def test_has_minutes(self):
        assert hasattr(TimeEntry, "minutes")

    def test_has_description(self):
        assert hasattr(TimeEntry, "description")

    def test_has_entry_date(self):
        assert hasattr(TimeEntry, "entry_date")

    def test_has_billable(self):
        assert hasattr(TimeEntry, "billable")

    def test_has_relationships(self):
        assert hasattr(TimeEntry, "matter")
        assert hasattr(TimeEntry, "task")
        assert hasattr(TimeEntry, "stakeholder")


class TestTimeEntryCreateSchema:
    """Verify TimeEntryCreate validation."""

    def test_valid_create(self):
        data = TimeEntryCreate(
            hours=2,
            minutes=30,
            description="Drafted probate petition",
            entry_date=date.today(),
        )
        assert data.hours == 2
        assert data.minutes == 30
        assert data.billable is True

    def test_with_task_id(self):
        data = TimeEntryCreate(
            task_id=uuid.uuid4(),
            hours=1,
            minutes=0,
            description="Reviewed documents",
            entry_date=date.today(),
        )
        assert data.task_id is not None

    def test_non_billable(self):
        data = TimeEntryCreate(
            hours=0,
            minutes=15,
            description="Internal call",
            entry_date=date.today(),
            billable=False,
        )
        assert data.billable is False

    def test_negative_hours_rejected(self):
        import pytest

        with pytest.raises(Exception):
            TimeEntryCreate(
                hours=-1,
                minutes=0,
                description="test",
                entry_date=date.today(),
            )

    def test_minutes_over_59_rejected(self):
        import pytest

        with pytest.raises(Exception):
            TimeEntryCreate(
                hours=0,
                minutes=60,
                description="test",
                entry_date=date.today(),
            )


class TestTimeEntryUpdateSchema:
    """Verify TimeEntryUpdate allows partial updates."""

    def test_all_none(self):
        data = TimeEntryUpdate()
        assert data.hours is None
        assert data.minutes is None

    def test_partial_update(self):
        data = TimeEntryUpdate(hours=3, description="Updated description")
        assert data.hours == 3
        assert data.minutes is None
        assert data.description == "Updated description"


class TestTimeEntryResponseSchema:
    """Verify TimeEntryResponse serialization."""

    def test_valid_response(self):
        resp = TimeEntryResponse(
            id=uuid.uuid4(),
            matter_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            task_title="File probate petition",
            stakeholder_id=uuid.uuid4(),
            stakeholder_name="Jane Doe",
            hours=2,
            minutes=15,
            description="Drafted petition",
            entry_date=date.today(),
            billable=True,
            created_at=datetime.now(),
        )
        assert resp.hours == 2
        assert resp.task_title == "File probate petition"

    def test_no_task(self):
        resp = TimeEntryResponse(
            id=uuid.uuid4(),
            matter_id=uuid.uuid4(),
            task_id=None,
            task_title=None,
            stakeholder_id=uuid.uuid4(),
            stakeholder_name="John Doe",
            hours=0,
            minutes=30,
            description="General admin",
            entry_date=date.today(),
            billable=False,
            created_at=datetime.now(),
        )
        assert resp.task_id is None
        assert resp.billable is False


class TestTimeTrackingSummarySchema:
    """Verify TimeTrackingSummary schema."""

    def test_valid_summary(self):
        summary = TimeTrackingSummary(
            total_hours=10,
            total_minutes=30,
            total_decimal_hours=10.5,
            billable_hours=8.0,
            non_billable_hours=2.5,
            by_stakeholder=[
                {"stakeholder_id": str(uuid.uuid4()), "name": "Jane", "total_minutes": 630, "decimal_hours": 10.5}
            ],
            by_task=[
                {"task_id": str(uuid.uuid4()), "title": "Review docs", "total_minutes": 120, "decimal_hours": 2.0}
            ],
        )
        assert summary.total_decimal_hours == 10.5
        assert len(summary.by_stakeholder) == 1


class TestTimeTrackingServiceSignatures:
    """Verify time tracking service functions exist with correct signatures."""

    def test_create_time_entry(self):
        import inspect

        from app.services.time_tracking_service import create_time_entry

        sig = inspect.signature(create_time_entry)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "matter_id" in params
        assert "stakeholder" in params
        assert "hours" in params
        assert "minutes" in params
        assert "description" in params

    def test_list_time_entries(self):
        import inspect

        from app.services.time_tracking_service import list_time_entries

        sig = inspect.signature(list_time_entries)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "matter_id" in params
        assert "task_id" in params
        assert "stakeholder_id" in params
        assert "billable" in params

    def test_update_time_entry(self):
        import inspect

        from app.services.time_tracking_service import update_time_entry

        sig = inspect.signature(update_time_entry)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "entry_id" in params

    def test_delete_time_entry(self):
        import inspect

        from app.services.time_tracking_service import delete_time_entry

        sig = inspect.signature(delete_time_entry)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "entry_id" in params

    def test_get_time_summary(self):
        import inspect

        from app.services.time_tracking_service import get_time_summary

        sig = inspect.signature(get_time_summary)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "matter_id" in params


class TestTimeTrackingReportIntegration:
    """Verify time tracking report is wired up."""

    def test_report_generator_registered(self):
        from app.services.report_service import REPORT_GENERATORS

        assert "time-tracking" in REPORT_GENERATORS
        assert "xlsx" in REPORT_GENERATORS["time-tracking"]["formats"]

    def test_report_uses_time_entries(self):
        import inspect

        from app.services.report_service import generate_time_tracking_xlsx

        source = inspect.getsource(generate_time_tracking_xlsx)
        assert "TimeEntry" in source
        assert "time_entrys" in source or "TimeEntry" in source

    def test_csv_export_exists_in_service(self):
        """Verify the service supports CSV-compatible data retrieval."""
        import inspect

        from app.services.time_tracking_service import list_time_entries

        # The list_time_entries function supports per_page=10000 for full export
        source = inspect.getsource(list_time_entries)
        assert "per_page" in source
        assert "entry_date" in source
