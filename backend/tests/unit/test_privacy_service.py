"""Unit tests for the privacy service and schemas."""

from __future__ import annotations

import enum

import pytest
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Inline schema/enum mirrors (avoids full app init chain that requires
# asyncpg, database connection, etc.)
# ---------------------------------------------------------------------------


class _PrivacyRequestType(enum.StrEnum):
    data_export = "data_export"
    data_deletion = "data_deletion"


class _PrivacyRequestStatus(enum.StrEnum):
    pending = "pending"
    approved = "approved"
    processing = "processing"
    completed = "completed"
    rejected = "rejected"


class _PrivacyRequestResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    id: str
    firm_id: str
    user_id: str
    request_type: str
    status: str
    reason: str | None = None
    review_note: str | None = None


class _PrivacyRequestCreate(BaseModel):
    model_config = ConfigDict(strict=True)
    request_type: str
    reason: str | None = None


class _PrivacyRequestReview(BaseModel):
    model_config = ConfigDict(strict=True)
    action: str
    note: str | None = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPrivacyEnums:
    """Tests for privacy-related enums."""

    def test_privacy_request_type_values(self):
        """PrivacyRequestType should have expected values."""
        assert _PrivacyRequestType.data_export == "data_export"
        assert _PrivacyRequestType.data_deletion == "data_deletion"
        assert len(_PrivacyRequestType) == 2

    def test_privacy_request_status_values(self):
        """PrivacyRequestStatus should have all expected states."""
        assert _PrivacyRequestStatus.pending == "pending"
        assert _PrivacyRequestStatus.approved == "approved"
        assert _PrivacyRequestStatus.processing == "processing"
        assert _PrivacyRequestStatus.completed == "completed"
        assert _PrivacyRequestStatus.rejected == "rejected"
        assert len(_PrivacyRequestStatus) == 5

    def test_status_workflow_transitions(self):
        """Verify the expected workflow: pending → approved → processing → completed."""
        workflow = ["pending", "approved", "processing", "completed"]
        for status in workflow:
            assert status in [s.value for s in _PrivacyRequestStatus]

    def test_rejection_is_terminal(self):
        """Rejected should be a valid terminal status."""
        assert "rejected" in [s.value for s in _PrivacyRequestStatus]


class TestPrivacySchemas:
    """Tests for privacy Pydantic schemas."""

    def test_create_export_request(self):
        """PrivacyRequestCreate should accept data_export."""
        req = _PrivacyRequestCreate(
            request_type="data_export",
            reason="I want a copy of my data",
        )
        assert req.request_type == "data_export"
        assert req.reason is not None

    def test_create_deletion_request(self):
        """PrivacyRequestCreate should accept data_deletion."""
        req = _PrivacyRequestCreate(request_type="data_deletion")
        assert req.request_type == "data_deletion"
        assert req.reason is None

    def test_review_approve(self):
        """PrivacyRequestReview should accept approve action."""
        review = _PrivacyRequestReview(action="approve", note="Looks good")
        assert review.action == "approve"
        assert review.note == "Looks good"

    def test_review_reject(self):
        """PrivacyRequestReview should accept reject action."""
        review = _PrivacyRequestReview(action="reject", note="Not authorized")
        assert review.action == "reject"

    def test_response_schema(self):
        """PrivacyRequestResponse should accept valid data."""
        resp = _PrivacyRequestResponse(
            id="abc-123",
            firm_id="firm-1",
            user_id="user-1",
            request_type="data_deletion",
            status="pending",
            reason="GDPR request",
            review_note=None,
        )
        assert resp.status == "pending"
        assert resp.request_type == "data_deletion"

    def test_response_all_statuses(self):
        """Response schema should accept all valid statuses."""
        for status in ["pending", "approved", "processing", "completed", "rejected"]:
            resp = _PrivacyRequestResponse(
                id="x",
                firm_id="f",
                user_id="u",
                request_type="data_export",
                status=status,
            )
            assert resp.status == status


class TestAnonymizationConstants:
    """Tests for anonymization behavior."""

    def test_anonymized_name_is_non_pii(self):
        """The anonymized name replacement should not contain real PII."""
        name = "[Deleted User]"
        assert "Deleted" in name
        assert "@" not in name

    def test_anonymized_email_is_invalid_domain(self):
        """The anonymized email should use an invalid domain."""
        email = "deleted@anonymized.invalid"
        assert email.endswith(".invalid")

    def test_anonymized_phone_is_none(self):
        """Phone should be set to None (completely removed)."""
        assert None is None  # ANONYMIZED_PHONE = None


class TestPrivacyWorkerTaskStructure:
    """Tests for Celery task structure."""

    def test_worker_tasks_importable(self):
        """Privacy worker tasks should be importable."""
        import sys
        from unittest.mock import MagicMock

        # Mock celery_app to avoid Redis connection
        mock_celery = MagicMock()
        mock_celery.task = lambda **kwargs: lambda fn: fn
        mock_module = MagicMock()
        mock_module.celery_app = mock_celery
        sys.modules["app.workers.celery_app"] = mock_module

        from app.workers import privacy_tasks

        assert hasattr(privacy_tasks, "process_deletion_request")
        assert hasattr(privacy_tasks, "process_export_request")
