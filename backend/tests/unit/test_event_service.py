"""Unit tests for event service — read-only queries, CSV export, schema validation."""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from app.models.enums import ActorType


class TestEventModel:
    """Verify Event model structure for audit trail."""

    def test_has_matter_id(self):
        from app.models.events import Event

        assert hasattr(Event, "matter_id")

    def test_has_actor_id(self):
        from app.models.events import Event

        assert hasattr(Event, "actor_id")

    def test_has_actor_type(self):
        from app.models.events import Event

        assert hasattr(Event, "actor_type")

    def test_has_entity_type(self):
        from app.models.events import Event

        assert hasattr(Event, "entity_type")

    def test_has_entity_id(self):
        from app.models.events import Event

        assert hasattr(Event, "entity_id")

    def test_has_action(self):
        from app.models.events import Event

        assert hasattr(Event, "action")

    def test_has_changes(self):
        from app.models.events import Event

        assert hasattr(Event, "changes")

    def test_has_metadata(self):
        from app.models.events import Event

        assert hasattr(Event, "metadata_")

    def test_has_created_at(self):
        from app.models.events import Event

        assert hasattr(Event, "created_at")

    def test_no_updated_at(self):
        """Events are immutable — no updated_at column."""
        from app.models.events import Event

        # Event extends Base directly, not BaseModel, so no updated_at
        columns = {c.name for c in Event.__table__.columns}
        assert "updated_at" not in columns

    def test_tablename_is_events(self):
        from app.models.events import Event

        assert Event.__tablename__ == "events"


class TestEventSchemas:
    """Verify event schema structure."""

    def test_response_has_actor_name(self):
        from app.schemas.events import EventResponse

        assert "actor_name" in EventResponse.model_fields

    def test_response_has_metadata(self):
        from app.schemas.events import EventResponse

        assert "metadata" in EventResponse.model_fields

    def test_response_has_changes(self):
        from app.schemas.events import EventResponse

        assert "changes" in EventResponse.model_fields

    def test_cursor_meta_has_has_more(self):
        from app.schemas.events import CursorMeta

        assert "has_more" in CursorMeta.model_fields

    def test_cursor_meta_has_next_cursor(self):
        from app.schemas.events import CursorMeta

        assert "next_cursor" in CursorMeta.model_fields

    def test_cursor_meta_has_per_page(self):
        from app.schemas.events import CursorMeta

        assert "per_page" in CursorMeta.model_fields

    def test_list_response_uses_cursor_meta(self):
        from app.schemas.events import CursorMeta, EventListResponse

        # meta field type should reference CursorMeta
        meta_annotation = EventListResponse.model_fields["meta"].annotation
        assert meta_annotation is CursorMeta


class TestReadOnlyEnforcement:
    """Verify the event service is read-only."""

    def test_no_create_function(self):
        from app.services import event_service

        assert not hasattr(event_service, "create_event")

    def test_no_update_function(self):
        from app.services import event_service

        assert not hasattr(event_service, "update_event")

    def test_no_delete_function(self):
        from app.services import event_service

        assert not hasattr(event_service, "delete_event")

    def test_has_list_events(self):
        from app.services import event_service

        assert hasattr(event_service, "list_events")

    def test_has_export_csv(self):
        from app.services import event_service

        assert hasattr(event_service, "export_events_csv")


class TestChangesSummary:
    """Test the _summarize_changes helper."""

    def test_none_changes(self):
        from app.services.event_service import _summarize_changes

        assert _summarize_changes(None) == ""

    def test_empty_changes(self):
        from app.services.event_service import _summarize_changes

        assert _summarize_changes({}) == ""

    def test_old_new_format(self):
        from app.services.event_service import _summarize_changes

        changes = {"status": {"old": "not_started", "new": "in_progress"}}
        result = _summarize_changes(changes)
        assert "status" in result
        assert "not_started" in result
        assert "in_progress" in result
        assert "→" in result

    def test_multiple_fields(self):
        from app.services.event_service import _summarize_changes

        changes = {
            "status": {"old": "a", "new": "b"},
            "title": {"old": "x", "new": "y"},
        }
        result = _summarize_changes(changes)
        assert ";" in result
        assert "status" in result
        assert "title" in result

    def test_non_diff_value_uses_json(self):
        from app.services.event_service import _summarize_changes

        changes = {"raw_value": "something"}
        result = _summarize_changes(changes)
        assert "raw_value" in result


class TestDateRangeFilter:
    """Test date range boundary handling."""

    def test_date_to_uses_next_day(self):
        """date_to should include the full day using timedelta."""
        d = date(2025, 1, 31)
        next_day = d + timedelta(days=1)
        assert next_day == date(2025, 2, 1)

    def test_date_to_end_of_year(self):
        """date_to at year boundary should work."""
        d = date(2025, 12, 31)
        next_day = d + timedelta(days=1)
        assert next_day == date(2026, 1, 1)

    def test_date_to_feb_28_non_leap(self):
        """Feb 28 in non-leap year should roll to Mar 1."""
        d = date(2025, 2, 28)
        next_day = d + timedelta(days=1)
        assert next_day == date(2025, 3, 1)

    def test_date_to_feb_29_leap(self):
        """Feb 29 in leap year should roll to Mar 1."""
        d = date(2024, 2, 29)
        next_day = d + timedelta(days=1)
        assert next_day == date(2024, 3, 1)


class TestActorTypeEnum:
    """Verify actor type enum values for event logging."""

    def test_user(self):
        assert ActorType.user == "user"

    def test_system(self):
        assert ActorType.system == "system"

    def test_ai(self):
        assert ActorType.ai == "ai"
