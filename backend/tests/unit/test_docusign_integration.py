"""Unit tests for DocuSign integration — client, service helpers, schemas."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.enums import SignatureRequestStatus, SignatureRequestType
from app.services.docusign_client import (
    build_authorize_url,
    generate_state,
    token_expires_at,
)

# ─── Enum tests ──────────────────────────────────────────────────────────────


class TestSignatureEnums:
    def test_status_values(self):
        expected = {
            "draft", "sent", "delivered", "signed",
            "completed", "declined", "voided", "expired",
        }
        assert {s.value for s in SignatureRequestStatus} == expected

    def test_type_values(self):
        expected = {
            "distribution_consent", "beneficiary_acknowledgment",
            "executor_oath", "general",
        }
        assert {t.value for t in SignatureRequestType} == expected

    def test_use_case_types_present(self):
        """Verify all documented use cases have corresponding types."""
        assert SignatureRequestType.distribution_consent.value == "distribution_consent"
        assert SignatureRequestType.beneficiary_acknowledgment.value == "beneficiary_acknowledgment"
        assert SignatureRequestType.executor_oath.value == "executor_oath"


# ─── OAuth helpers ───────────────────────────────────────────────────────────


class TestDocuSignOAuth:
    def test_generate_state_unique(self):
        states = {generate_state() for _ in range(10)}
        assert len(states) == 10

    def test_authorize_url_contains_params(self):
        url = build_authorize_url("test-state")
        assert "response_type=code" in url
        assert "state=test-state" in url
        assert "scope=signature" in url

    def test_authorize_url_starts_with_docusign(self):
        url = build_authorize_url("s")
        assert url.startswith("https://account-d.docusign.com/oauth/auth")

    def test_token_expires_at_default(self):
        from datetime import timedelta

        before = datetime.now(UTC)
        result = token_expires_at(None)
        assert result >= before + timedelta(seconds=3599)

    def test_token_expires_at_custom(self):
        from datetime import timedelta

        before = datetime.now(UTC)
        result = token_expires_at(1800)
        assert result >= before + timedelta(seconds=1799)
        assert result <= before + timedelta(seconds=1801)


# ─── DocuSignAPI client ──────────────────────────────────────────────────────


class TestDocuSignAPI:
    def test_headers_contain_bearer(self):
        from app.services.docusign_client import DocuSignAPI

        api = DocuSignAPI("test-token", "12345")
        headers = api._headers()
        assert headers["Authorization"] == "Bearer test-token"

    def test_base_url_includes_account(self):
        from app.services.docusign_client import DocuSignAPI

        api = DocuSignAPI("tok", "acc-123")
        assert "acc-123" in api._base


# ─── Status mapping helpers ──────────────────────────────────────────────────


class _FakeSigReq:
    def __init__(self):
        self.status = SignatureRequestStatus.sent
        self.completed_at = None
        self.signers = [
            {"email": "test@example.com", "name": "Test", "role": "signer"},
        ]


class TestStatusHelpers:
    def test_update_status_from_envelope(self):
        from app.services.docusign_service import _update_status_from_envelope

        sig = _FakeSigReq()
        _update_status_from_envelope(sig, {"status": "completed"})
        assert sig.status == SignatureRequestStatus.completed
        assert sig.completed_at is not None

    def test_update_status_unknown(self):
        from app.services.docusign_service import _update_status_from_envelope

        sig = _FakeSigReq()
        _update_status_from_envelope(sig, {"status": "some_new_status"})
        assert sig.status == SignatureRequestStatus.sent  # unchanged

    def test_update_signers_from_recipients(self):
        from app.services.docusign_service import _update_signers_from_recipients

        sig = _FakeSigReq()
        recipients = {
            "signers": [
                {
                    "email": "test@example.com",
                    "status": "completed",
                    "signedDateTime": "2026-03-24T12:00:00Z",
                }
            ]
        }
        _update_signers_from_recipients(sig, recipients)
        assert sig.signers[0]["status"] == "completed"
        assert sig.signers[0]["signed_at"] == "2026-03-24T12:00:00Z"

    def test_update_signers_no_match(self):
        from app.services.docusign_service import _update_signers_from_recipients

        sig = _FakeSigReq()
        recipients = {
            "signers": [
                {"email": "other@example.com", "status": "sent"}
            ]
        }
        _update_signers_from_recipients(sig, recipients)
        # No match, original signer unchanged
        assert "status" not in sig.signers[0]


# ─── Schema tests ────────────────────────────────────────────────────────────


class TestDocuSignSchemas:
    def test_send_request_validates(self):
        from uuid import uuid4

        from app.schemas.docusign import SendForSignatureRequest

        req = SendForSignatureRequest(
            document_id=uuid4(),
            subject="Please sign",
            signers=[
                {"email": "signer@example.com", "name": "Jane Doe"},
            ],
        )
        assert req.request_type == "general"
        assert len(req.signers) == 1

    def test_send_request_with_type(self):
        from uuid import uuid4

        from app.schemas.docusign import SendForSignatureRequest

        req = SendForSignatureRequest(
            document_id=uuid4(),
            subject="Executor Oath",
            request_type="executor_oath",
            signers=[
                {"email": "exec@example.com", "name": "John Smith"},
            ],
        )
        assert req.request_type == "executor_oath"

    def test_void_request_default_reason(self):
        from app.schemas.docusign import VoidEnvelopeRequest

        req = VoidEnvelopeRequest()
        assert "Voided" in req.reason

    def test_signature_response_from_dict(self):
        from uuid import uuid4

        from app.schemas.docusign import SignatureRequestResponse

        data = {
            "id": uuid4(),
            "matter_id": uuid4(),
            "request_type": "distribution_consent",
            "status": "sent",
            "subject": "Sign this",
            "signers": [{"email": "a@b.com", "name": "A", "role": "signer"}],
            "sent_by": uuid4(),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        resp = SignatureRequestResponse(**data)
        assert resp.status == "sent"
        assert resp.request_type == "distribution_consent"
