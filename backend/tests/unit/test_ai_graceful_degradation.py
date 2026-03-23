"""Tests for AI graceful degradation — ensuring the app works without AI.

Verifies that:
- AI service errors return 503 with helpful messages (not raw 500s)
- Rate limit exceeded returns 429
- Manual classification always works regardless of AI status
- Partial extraction results are still usable
- Documents without AI classification remain fully functional
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.ai_rate_limiter import RateLimitExceededError


class TestAPIErrorResponses:
    """Verify AI API routes return clean error responses, not raw 500s."""

    def test_route_file_has_error_handler(self):
        """The AI routes file should have a _handle_ai_error function."""
        route_file = Path(__file__).parents[2] / "app" / "api" / "v1" / "ai" / "__init__.py"
        source = route_file.read_text()
        assert "_handle_ai_error" in source
        assert "503" in source
        assert "429" in source
        assert "ai_unavailable" in source
        assert "rate_limit_exceeded" in source

    def test_all_ai_endpoints_catch_general_exceptions(self):
        """Every AI endpoint should catch Exception (not just ValueError)."""
        route_file = Path(__file__).parents[2] / "app" / "api" / "v1" / "ai" / "__init__.py"
        source = route_file.read_text()
        # Count "except Exception as exc:" — should be at least 5 (one per AI endpoint)
        general_catches = source.count("except Exception as exc:")
        assert general_catches >= 5, f"Only {general_catches} general exception handlers found"

    def test_rate_limit_returns_429_message(self):
        """RateLimitExceededError should produce a 429 response with helpful message."""
        # Import inline to avoid jwt chain
        route_file = Path(__file__).parents[2] / "app" / "api" / "v1" / "ai" / "__init__.py"
        source = route_file.read_text()
        assert "rate_limit_exceeded" in source
        assert "try again later" in source.lower()

    def test_unavailable_returns_manual_fallback_message(self):
        """503 response should tell user they can use manual features."""
        route_file = Path(__file__).parents[2] / "app" / "api" / "v1" / "ai" / "__init__.py"
        source = route_file.read_text()
        assert "manual features" in source.lower() or "manual" in source.lower()


class TestManualClassificationFallback:
    """Verify manual classification works without AI."""

    @pytest.mark.asyncio
    async def test_confirm_doc_type_works_without_ai(self):
        """confirm_doc_type should work even if AI services are down."""
        from app.services.document_service import confirm_doc_type

        mock_db = AsyncMock()

        mock_doc = MagicMock()
        mock_doc.id = uuid4()
        mock_doc.matter_id = uuid4()
        mock_doc.doc_type = None
        mock_doc.doc_type_confidence = None
        mock_doc.doc_type_confirmed = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        mock_user = MagicMock()
        mock_user.user_id = uuid4()
        mock_user.firm_id = uuid4()

        with (
            patch(
                "app.services.document_service.event_logger.log",
                new_callable=AsyncMock,
            ),
            # AI feedback service fails — should NOT break confirm_doc_type
            patch(
                "app.services.ai_feedback_service.log_classification_correction",
                side_effect=Exception("AI service down"),
            ),
        ):
            await confirm_doc_type(
                mock_db,
                doc_id=mock_doc.id,
                matter_id=mock_doc.matter_id,
                doc_type="death_certificate",
                current_user=mock_user,
            )

        # Document should still be updated even if AI feedback logging fails
        assert mock_doc.doc_type == "death_certificate"
        assert mock_doc.doc_type_confirmed is True

    @pytest.mark.asyncio
    async def test_confirm_doc_type_sets_type_from_none(self):
        """User can manually classify a document that AI never classified."""
        from app.services.document_service import confirm_doc_type

        mock_db = AsyncMock()

        mock_doc = MagicMock()
        mock_doc.id = uuid4()
        mock_doc.matter_id = uuid4()
        mock_doc.doc_type = None  # AI never classified
        mock_doc.doc_type_confidence = None
        mock_doc.doc_type_confirmed = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        mock_user = MagicMock()
        mock_user.user_id = uuid4()
        mock_user.firm_id = uuid4()

        with (
            patch("app.services.document_service.event_logger.log", new_callable=AsyncMock),
            patch(
                "app.services.ai_feedback_service.log_classification_correction",
                new_callable=AsyncMock,
            ),
        ):
            await confirm_doc_type(
                mock_db,
                doc_id=mock_doc.id,
                matter_id=mock_doc.matter_id,
                doc_type="will",
                current_user=mock_user,
            )

        assert mock_doc.doc_type == "will"
        assert mock_doc.doc_type_confirmed is True


class TestPartialExtractionResults:
    """Verify partial extraction results are still usable."""

    @pytest.mark.asyncio
    async def test_extraction_with_some_null_fields_is_valid(self):
        """Extraction with some null fields should still return valid response."""
        from app.schemas.ai import AIExtractResponse

        # Partial result — some fields null
        resp = AIExtractResponse(
            extracted_fields={
                "institution": "Chase Bank",
                "account_type": None,
                "balance": 50000,
                "account_number_last4": None,
                "as_of_date": None,
            },
            confidence=0.6,
        )

        # Non-null fields should be accessible
        assert resp.extracted_fields["institution"] == "Chase Bank"
        assert resp.extracted_fields["balance"] == 50000
        # Null fields should be present but null
        assert resp.extracted_fields["account_type"] is None

    @pytest.mark.asyncio
    async def test_empty_extraction_returns_valid_response(self):
        from app.schemas.ai import AIExtractResponse

        resp = AIExtractResponse(extracted_fields={}, confidence=0.0)
        assert resp.extracted_fields == {}
        assert resp.confidence == 0.0

    @pytest.mark.asyncio
    async def test_extraction_failure_sets_document_metadata(self):
        """When extraction fails, document gets a status marker."""
        from app.services.ai_extraction_service import extract_document_data

        mock_db = AsyncMock()
        doc_id = uuid4()

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.matter_id = uuid4()
        mock_doc.doc_type = "account_statement"
        mock_doc.storage_key = "test.pdf"
        mock_doc.mime_type = "application/pdf"
        mock_doc.ai_extracted_data = None

        mock_matter = MagicMock()
        mock_matter.id = mock_doc.matter_id
        mock_matter.firm_id = uuid4()

        r1 = MagicMock()
        r1.scalar_one_or_none.return_value = mock_doc
        r2 = MagicMock()
        r2.scalar_one_or_none.return_value = mock_matter
        mock_db.execute.side_effect = [r1, r2]

        with (
            patch("app.services.ai_extraction_service.check_rate_limit"),
            patch(
                "app.services.ai_extraction_service.text_extraction_service.extract_text",
                return_value="",
            ),
        ):
            result = await extract_document_data(mock_db, document_id=doc_id)

        assert result.extracted_fields == {}
        assert result.confidence == 0.0
        # Document should have extraction_status set
        assert mock_doc.ai_extracted_data is not None
        assert mock_doc.ai_extracted_data.get("extraction_status") == "failed"


class TestCeleryTaskResilience:
    """Verify Celery tasks handle failures gracefully."""

    def test_classify_task_retries_on_failure(self):
        """classify_document task should retry, not crash permanently."""
        from app.workers.ai_tasks import classify_document

        assert classify_document.max_retries == 3

    def test_extract_task_retries_on_failure(self):
        from app.workers.ai_tasks import extract_document_data

        assert extract_document_data.max_retries == 3

    def test_draft_task_retries_on_failure(self):
        from app.workers.ai_tasks import draft_letter

        assert draft_letter.max_retries == 3

    def test_classify_has_time_limits(self):
        """Tasks should have time limits to prevent queue blocking."""
        from app.workers.ai_tasks import classify_document

        # soft_time_limit should be set (raises SoftTimeLimitExceeded)
        assert classify_document.soft_time_limit is not None
        assert classify_document.time_limit is not None


class TestRateLimiterResilience:
    """Verify rate limiter doesn't block when Redis is down."""

    @patch("app.services.ai_rate_limiter._get_redis")
    def test_redis_connection_error_swallowed(self, mock_get_redis):
        from app.services.ai_rate_limiter import check_rate_limit

        mock_get_redis.side_effect = ConnectionError("Redis is down")
        # Should NOT raise — processing continues
        check_rate_limit(firm_id=uuid4(), matter_id=uuid4())

    @patch("app.services.ai_rate_limiter._get_redis")
    def test_redis_timeout_swallowed(self, mock_get_redis):
        from app.services.ai_rate_limiter import check_rate_limit

        mock_get_redis.side_effect = TimeoutError("Redis timed out")
        check_rate_limit(firm_id=uuid4(), matter_id=uuid4())

    @patch("app.services.ai_rate_limiter._get_redis")
    def test_rate_limit_exceeded_still_propagates(self, mock_get_redis):
        """RateLimitExceededError should still be raised (it's intentional, not an error)."""
        from app.services.ai_rate_limiter import check_rate_limit

        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis
        mock_redis.eval.return_value = -1

        with pytest.raises(RateLimitExceededError):
            check_rate_limit(firm_id=uuid4(), matter_id=uuid4())


class TestFrontendGracefulDegradation:
    """Verify frontend components have manual fallbacks (source-level checks)."""

    def test_document_panel_has_manual_classify_button(self):
        panel_file = (
            Path(__file__).parents[3]
            / "frontend"
            / "src"
            / "app"
            / "(dashboard)"
            / "matters"
            / "[matterId]"
            / "documents"
            / "_components"
            / "DocumentDetailPanel.tsx"
        )
        source = panel_file.read_text()
        assert "Classify Manually" in source

    def test_insights_panel_shows_manual_fallback_message(self):
        panel_file = (
            Path(__file__).parents[3]
            / "frontend"
            / "src"
            / "app"
            / "(dashboard)"
            / "matters"
            / "[matterId]"
            / "_components"
            / "AIInsightsPanel.tsx"
        )
        source = panel_file.read_text()
        assert "manually" in source.lower()

    def test_letter_dialog_shows_fallback_message(self):
        dialog_file = (
            Path(__file__).parents[3]
            / "frontend"
            / "src"
            / "app"
            / "(dashboard)"
            / "matters"
            / "[matterId]"
            / "assets"
            / "_components"
            / "DraftLetterDialog.tsx"
        )
        source = dialog_file.read_text()
        assert "manually" in source.lower() or "try again" in source.lower()

    def test_extract_button_shows_error_message(self):
        panel_file = (
            Path(__file__).parents[3]
            / "frontend"
            / "src"
            / "app"
            / "(dashboard)"
            / "matters"
            / "[matterId]"
            / "documents"
            / "_components"
            / "DocumentDetailPanel.tsx"
        )
        source = panel_file.read_text()
        assert "extraction unavailable" in source.lower() or "enter data manually" in source.lower()
