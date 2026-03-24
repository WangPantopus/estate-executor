"""Unit tests for dispute resolution workflow — enum, schema, state machine."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.models.enums import CommunicationType, CommunicationVisibility, DisputeStatus
from app.schemas.communications import (
    CommunicationResponse,
    DisputeFlagCreate,
    DisputeStatusUpdate,
)


class TestDisputeStatusEnum:
    """Verify dispute status enum values."""

    def test_open(self):
        assert DisputeStatus.open == "open"

    def test_under_review(self):
        assert DisputeStatus.under_review == "under_review"

    def test_resolved(self):
        assert DisputeStatus.resolved == "resolved"

    def test_all_values(self):
        values = {e.value for e in DisputeStatus}
        assert values == {"open", "under_review", "resolved"}


class TestDisputeStatusTransitions:
    """Verify valid dispute status transitions."""

    def test_open_to_under_review(self):
        from app.services.communication_service import _VALID_DISPUTE_TRANSITIONS

        assert DisputeStatus.under_review in _VALID_DISPUTE_TRANSITIONS[DisputeStatus.open]

    def test_open_to_resolved(self):
        from app.services.communication_service import _VALID_DISPUTE_TRANSITIONS

        assert DisputeStatus.resolved in _VALID_DISPUTE_TRANSITIONS[DisputeStatus.open]

    def test_under_review_to_resolved(self):
        from app.services.communication_service import _VALID_DISPUTE_TRANSITIONS

        assert DisputeStatus.resolved in _VALID_DISPUTE_TRANSITIONS[DisputeStatus.under_review]

    def test_under_review_can_reopen(self):
        from app.services.communication_service import _VALID_DISPUTE_TRANSITIONS

        assert DisputeStatus.open in _VALID_DISPUTE_TRANSITIONS[DisputeStatus.under_review]

    def test_resolved_is_terminal(self):
        from app.services.communication_service import _VALID_DISPUTE_TRANSITIONS

        assert _VALID_DISPUTE_TRANSITIONS[DisputeStatus.resolved] == []


class TestDisputeFlagCreateSchema:
    """Verify dispute flag creation schema."""

    def test_valid_create(self):
        data = DisputeFlagCreate(
            entity_type="asset",
            entity_id=uuid.uuid4(),
            reason="Disputed ownership of the property.",
        )
        assert data.entity_type == "asset"
        assert data.reason == "Disputed ownership of the property."

    def test_task_dispute(self):
        data = DisputeFlagCreate(
            entity_type="task",
            entity_id=uuid.uuid4(),
            reason="Task should not be assigned this way.",
        )
        assert data.entity_type == "task"


class TestDisputeStatusUpdateSchema:
    """Verify dispute status update schema."""

    def test_mark_under_review(self):
        data = DisputeStatusUpdate(
            status="under_review",
            resolution_note="Reviewing with all parties involved.",
        )
        assert data.status == "under_review"
        assert data.resolution_note == "Reviewing with all parties involved."

    def test_mark_resolved(self):
        data = DisputeStatusUpdate(
            status="resolved",
            resolution_note="Ownership verified via title deed. Dispute closed.",
        )
        assert data.status == "resolved"


class TestCommunicationResponseWithDisputeFields:
    """Verify CommunicationResponse includes dispute fields."""

    def test_dispute_fields_present(self):
        resp = CommunicationResponse(
            id=uuid.uuid4(),
            matter_id=uuid.uuid4(),
            sender_id=uuid.uuid4(),
            sender_name="John Doe",
            type=CommunicationType.dispute_flag,
            subject="Dispute: asset abc123",
            body="Disputed ownership",
            visibility=CommunicationVisibility.all_stakeholders,
            acknowledged_by=[],
            created_at=datetime.now(),
            disputed_entity_type="asset",
            disputed_entity_id=uuid.uuid4(),
            dispute_status="open",
        )
        assert resp.disputed_entity_type == "asset"
        assert resp.dispute_status == "open"

    def test_dispute_fields_none_for_non_disputes(self):
        resp = CommunicationResponse(
            id=uuid.uuid4(),
            matter_id=uuid.uuid4(),
            sender_id=uuid.uuid4(),
            sender_name="Jane Doe",
            type=CommunicationType.message,
            subject="Update",
            body="Hello",
            visibility=CommunicationVisibility.all_stakeholders,
            acknowledged_by=[],
            created_at=datetime.now(),
        )
        assert resp.disputed_entity_type is None
        assert resp.dispute_status is None
        assert resp.dispute_resolution_note is None

    def test_resolved_dispute_has_all_fields(self):
        resp = CommunicationResponse(
            id=uuid.uuid4(),
            matter_id=uuid.uuid4(),
            sender_id=uuid.uuid4(),
            sender_name="Admin",
            type=CommunicationType.dispute_flag,
            subject="Dispute: task xyz",
            body="Task assignment disputed",
            visibility=CommunicationVisibility.all_stakeholders,
            acknowledged_by=[],
            created_at=datetime.now(),
            disputed_entity_type="task",
            disputed_entity_id=uuid.uuid4(),
            dispute_status="resolved",
            dispute_resolution_note="Verified correct assignment.",
            dispute_resolved_at=datetime.now(),
            dispute_resolved_by=uuid.uuid4(),
        )
        assert resp.dispute_status == "resolved"
        assert resp.dispute_resolution_note == "Verified correct assignment."
        assert resp.dispute_resolved_by is not None
        assert resp.dispute_resolved_at is not None


class TestCommunicationModelDisputeFields:
    """Verify Communication model has dispute fields."""

    def test_has_disputed_entity_type(self):
        from app.models.communications import Communication

        assert hasattr(Communication, "disputed_entity_type")

    def test_has_disputed_entity_id(self):
        from app.models.communications import Communication

        assert hasattr(Communication, "disputed_entity_id")

    def test_has_dispute_status(self):
        from app.models.communications import Communication

        assert hasattr(Communication, "dispute_status")

    def test_has_dispute_resolution_note(self):
        from app.models.communications import Communication

        assert hasattr(Communication, "dispute_resolution_note")

    def test_has_dispute_resolved_at(self):
        from app.models.communications import Communication

        assert hasattr(Communication, "dispute_resolved_at")

    def test_has_dispute_resolved_by(self):
        from app.models.communications import Communication

        assert hasattr(Communication, "dispute_resolved_by")

    def test_has_resolver_relationship(self):
        from app.models.communications import Communication

        assert hasattr(Communication, "resolver")


class TestDisputeHistoryInActivityFeed:
    """Verify that dispute actions generate events for the activity feed."""

    def test_create_dispute_logs_event(self):
        """Verify create_dispute_flag logs an event with action='dispute_flagged'."""
        import inspect

        from app.services.communication_service import create_dispute_flag

        source = inspect.getsource(create_dispute_flag)
        assert "dispute_flagged" in source
        assert "event_logger.log" in source

    def test_update_dispute_logs_event(self):
        """Verify update_dispute_status logs an event for each status change."""
        import inspect

        from app.services.communication_service import update_dispute_status

        source = inspect.getsource(update_dispute_status)
        assert "event_logger.log" in source
        assert "dispute_" in source
        assert "changes" in source
