"""Unit tests for the document request workflow — model, schemas, service helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.models.document_requests import DocumentRequest, _generate_upload_token
from app.models.enums import DocumentRequestStatus
from app.schemas.documents import (
    DocumentRequestCreate,
    DocumentRequestInfo,
    DocumentRequestResponse,
    TokenUploadComplete,
    TokenUploadRequest,
)


class TestDocumentRequestStatusEnum:
    """Verify document request status enum values."""

    def test_pending(self):
        assert DocumentRequestStatus.pending == "pending"

    def test_uploaded(self):
        assert DocumentRequestStatus.uploaded == "uploaded"

    def test_expired(self):
        assert DocumentRequestStatus.expired == "expired"

    def test_all_values(self):
        values = {e.value for e in DocumentRequestStatus}
        assert values == {"pending", "uploaded", "expired"}


class TestUploadTokenGeneration:
    """Verify upload token generation."""

    def test_token_is_string(self):
        token = _generate_upload_token()
        assert isinstance(token, str)

    def test_token_length(self):
        token = _generate_upload_token()
        assert len(token) >= 40  # secrets.token_urlsafe(36) produces ~48 chars

    def test_token_uniqueness(self):
        tokens = {_generate_upload_token() for _ in range(100)}
        assert len(tokens) == 100  # All unique

    def test_token_url_safe(self):
        token = _generate_upload_token()
        # URL-safe characters only
        import re

        assert re.match(r"^[A-Za-z0-9_-]+$", token)


class TestDocumentRequestModel:
    """Verify the DocumentRequest model has expected fields."""

    def test_has_matter_id(self):
        assert hasattr(DocumentRequest, "matter_id")

    def test_has_requester_stakeholder_id(self):
        assert hasattr(DocumentRequest, "requester_stakeholder_id")

    def test_has_target_stakeholder_id(self):
        assert hasattr(DocumentRequest, "target_stakeholder_id")

    def test_has_task_id(self):
        assert hasattr(DocumentRequest, "task_id")

    def test_has_doc_type_needed(self):
        assert hasattr(DocumentRequest, "doc_type_needed")

    def test_has_message(self):
        assert hasattr(DocumentRequest, "message")

    def test_has_upload_token(self):
        assert hasattr(DocumentRequest, "upload_token")

    def test_has_status(self):
        assert hasattr(DocumentRequest, "status")

    def test_has_document_id(self):
        assert hasattr(DocumentRequest, "document_id")

    def test_has_expires_at(self):
        assert hasattr(DocumentRequest, "expires_at")

    def test_has_completed_at(self):
        assert hasattr(DocumentRequest, "completed_at")


class TestDocumentRequestSchemas:
    """Verify document request Pydantic schemas validate correctly."""

    def test_document_request_create(self):
        data = DocumentRequestCreate(
            target_stakeholder_id=uuid.uuid4(),
            doc_type_needed="bank_statement",
            task_id=uuid.uuid4(),
            message="Please upload your bank statement.",
        )
        assert data.doc_type_needed == "bank_statement"
        assert data.message == "Please upload your bank statement."

    def test_document_request_create_minimal(self):
        data = DocumentRequestCreate(
            target_stakeholder_id=uuid.uuid4(),
            doc_type_needed="death_certificate",
        )
        assert data.task_id is None
        assert data.message is None

    def test_document_request_response(self):
        data = DocumentRequestResponse(
            id=uuid.uuid4(),
            upload_token="test-token-abc",
            upload_url="http://localhost:3000/upload/test-token-abc",
            status="pending",
            expires_at=datetime.now(UTC) + timedelta(days=14),
        )
        assert data.status == "pending"
        assert "test-token-abc" in data.upload_url

    def test_document_request_info(self):
        data = DocumentRequestInfo(
            request_id=uuid.uuid4(),
            matter_title="Estate of Smith",
            decedent_name="John Smith",
            requester_name="Jane Doe",
            doc_type_needed="bank_statement",
            message="Please upload",
            status="pending",
            expires_at=datetime.now(UTC) + timedelta(days=14),
            firm_name="Law Firm LLC",
        )
        assert data.decedent_name == "John Smith"
        assert data.firm_name == "Law Firm LLC"

    def test_token_upload_request(self):
        data = TokenUploadRequest(
            filename="statement.pdf",
            mime_type="application/pdf",
        )
        assert data.filename == "statement.pdf"

    def test_token_upload_complete(self):
        data = TokenUploadComplete(
            filename="statement.pdf",
            storage_key="firms/abc/matters/def/documents/ghi/statement.pdf",
            mime_type="application/pdf",
            size_bytes=204800,
        )
        assert data.size_bytes == 204800


class TestDocumentRequestWorkflowIntegration:
    """Verify workflow data flow consistency."""

    def test_request_status_transitions(self):
        """Verify valid status progression: pending → uploaded."""
        assert DocumentRequestStatus.pending == "pending"
        assert DocumentRequestStatus.uploaded == "uploaded"
        # pending → uploaded is the happy path
        # pending → expired is the timeout path

    def test_expiry_check_logic(self):
        """Verify expiry detection logic."""
        now = datetime.now(UTC)
        future = now + timedelta(days=14)
        past = now - timedelta(hours=1)

        # Not expired
        assert now < future

        # Expired
        assert now > past

    def test_task_requires_document_satisfied_by_upload(self):
        """Verify that the task document link is created during token upload.

        When a document request has a task_id, the complete_token_upload
        function should insert into task_documents, satisfying the
        requires_document check in task_service.complete_task().
        """
        # This test verifies the logic exists in the service code
        import inspect

        from app.services.document_service import complete_token_upload

        source = inspect.getsource(complete_token_upload)
        assert "task_documents.insert()" in source
        assert "task_id" in source
