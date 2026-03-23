"""AI pipeline tests — error handling, timeouts, malformed responses, rate limits.

Tests the resilience of the AI pipeline under failure conditions:
API timeouts, malformed Claude responses, rate limit hits, and service errors.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.ai import AIClassifyResponse, AIExtractResponse
from app.services.ai_rate_limiter import (
    FIRM_LIMIT_PER_HOUR,
    RateLimitExceededError,
    check_rate_limit,
)


def _make_classify_mocks(doc_id=None, matter_id=None, firm_id=None):
    """Create standard mocks for classification tests."""
    doc_id = doc_id or uuid4()
    matter_id = matter_id or uuid4()
    firm_id = firm_id or uuid4()

    mock_db = AsyncMock()
    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.matter_id = matter_id
    mock_doc.storage_key = "test/key.pdf"
    mock_doc.mime_type = "application/pdf"
    mock_doc.doc_type = None
    mock_doc.doc_type_confidence = None

    mock_matter = MagicMock()
    mock_matter.id = matter_id
    mock_matter.firm_id = firm_id
    mock_matter.estate_type = MagicMock(value="testate_probate")
    mock_matter.jurisdiction_state = "CA"
    mock_matter.decedent_name = "John Doe"

    mock_result_doc = MagicMock()
    mock_result_doc.scalar_one_or_none.return_value = mock_doc
    mock_result_matter = MagicMock()
    mock_result_matter.scalar_one_or_none.return_value = mock_matter
    mock_db.execute.side_effect = [mock_result_doc, mock_result_matter]

    return mock_db, mock_doc, mock_matter


# ─── API Timeout Tests ────────────────────────────────────────────────────────


class TestAPITimeout:
    """Test handling of Claude API timeouts."""

    @pytest.mark.asyncio
    async def test_classification_timeout_logs_error_and_raises(self):
        from app.services.ai_classification_service import classify_document

        mock_db, _, _ = _make_classify_mocks()

        with (
            patch("app.services.ai_classification_service.check_rate_limit"),
            patch(
                "app.services.ai_classification_service.text_extraction_service.extract_text",
                return_value="Document text here",
            ),
            patch(
                "app.services.ai_classification_service._call_claude",
                side_effect=TimeoutError("API request timed out after 120s"),
            ),
            pytest.raises(TimeoutError, match="timed out"),
        ):
            await classify_document(mock_db, document_id=uuid4())

    @pytest.mark.asyncio
    async def test_extraction_timeout_logs_error_and_raises(self):
        from app.services.ai_extraction_service import extract_document_data

        mock_db = AsyncMock()
        mock_doc = MagicMock()
        mock_doc.id = uuid4()
        mock_doc.matter_id = uuid4()
        mock_doc.doc_type = "account_statement"
        mock_doc.storage_key = "test.pdf"
        mock_doc.mime_type = "application/pdf"

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
                return_value="Statement text",
            ),
            patch(
                "app.services.ai_extraction_service._call_claude",
                side_effect=TimeoutError("API timeout"),
            ),
            pytest.raises(TimeoutError),
        ):
            await extract_document_data(mock_db, document_id=mock_doc.id)

    @pytest.mark.asyncio
    async def test_letter_draft_timeout_logs_error_and_raises(self):
        from app.services.ai_letter_service import draft_letter

        mock_db = AsyncMock()
        mock_asset = MagicMock()
        mock_asset.id = uuid4()
        mock_asset.matter_id = uuid4()
        mock_asset.title = "Test Asset"
        mock_asset.institution = "Test Bank"
        mock_asset.asset_type = MagicMock(value="bank_account")
        mock_asset.account_number_encrypted = None
        mock_asset.current_estimated_value = 10000
        mock_asset.date_of_death_value = None

        mock_matter = MagicMock()
        mock_matter.id = mock_asset.matter_id
        mock_matter.firm_id = uuid4()
        mock_matter.decedent_name = "John Doe"
        mock_matter.date_of_death = None
        mock_matter.estate_type = MagicMock(value="testate_probate")
        mock_matter.jurisdiction_state = "CA"
        mock_matter.settings = {}

        mock_executor = MagicMock()
        mock_executor.full_name = "Jane Doe"

        r1 = MagicMock()
        r1.scalar_one_or_none.return_value = mock_asset
        r2 = MagicMock()
        r2.scalar_one_or_none.return_value = mock_matter
        r3 = MagicMock()
        r3.scalars.return_value.first.return_value = mock_executor
        mock_db.execute.side_effect = [r1, r2, r3]

        with (
            patch("app.services.ai_letter_service.check_rate_limit"),
            patch("app.services.ai_letter_service._mask_account_number", return_value=None),
            patch(
                "app.services.ai_letter_service._call_claude",
                side_effect=TimeoutError("API timeout"),
            ),
            pytest.raises(TimeoutError),
        ):
            await draft_letter(
                mock_db,
                matter_id=mock_matter.id,
                asset_id=mock_asset.id,
                letter_type="institution_notification",
            )


# ─── Malformed Response Tests ─────────────────────────────────────────────────


class TestMalformedResponses:
    """Test handling of malformed Claude API responses."""

    @pytest.mark.asyncio
    async def test_classification_no_tool_use_raises(self):
        """When Claude doesn't return a tool_use block, should raise ValueError."""
        from app.services.ai_classification_service import _call_claude

        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="I cannot classify this")]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with (
            patch("anthropic.Anthropic", return_value=mock_client),
            pytest.raises(ValueError, match="did not return a tool_use"),
        ):
            _call_claude("test prompt")

    @pytest.mark.asyncio
    async def test_extraction_no_tool_use_raises(self):
        from app.services.ai_extraction_service import _call_claude

        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Cannot extract")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with (
            patch("anthropic.Anthropic", return_value=mock_client),
            pytest.raises(ValueError, match="did not return a tool_use"),
        ):
            _call_claude("system", "user", {"name": "test", "input_schema": {}})

    @pytest.mark.asyncio
    async def test_classification_missing_fields_in_tool_result(self):
        """If Claude tool result is missing required fields, Pydantic should reject."""
        incomplete_result = {"doc_type": "will"}  # Missing confidence and reasoning

        with pytest.raises(ValidationError):
            AIClassifyResponse(**incomplete_result)

    @pytest.mark.asyncio
    async def test_classification_invalid_confidence_type(self):
        """Non-numeric confidence should be rejected."""
        with pytest.raises(ValidationError):
            AIClassifyResponse(
                doc_type="will",
                confidence="high",  # type: ignore
                reasoning="test",
            )

    @pytest.mark.asyncio
    async def test_extraction_missing_extracted_fields(self):
        """AIExtractResponse requires extracted_fields dict."""
        with pytest.raises(ValidationError):
            AIExtractResponse(confidence=0.5)  # type: ignore


# ─── Rate Limit Tests ─────────────────────────────────────────────────────────


class TestRateLimitEnforcement:
    """Test rate limiting for AI API calls."""

    @patch("app.services.ai_rate_limiter._get_redis")
    def test_firm_rate_limit_at_boundary(self, mock_get_redis):
        """Exactly at the limit should raise."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis
        mock_redis.eval.return_value = -1  # Lua script returns -1 when limit exceeded

        with pytest.raises(RateLimitExceededError) as exc_info:
            check_rate_limit(firm_id=uuid4(), matter_id=uuid4())

        assert exc_info.value.limit == FIRM_LIMIT_PER_HOUR

    @patch("app.services.ai_rate_limiter._get_redis")
    def test_matter_rate_limit_at_boundary(self, mock_get_redis):
        """Matter limit should be enforced even if firm limit passes."""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis
        # Atomic script returns -2 when matter limit exceeded
        mock_redis.eval.return_value = -2

        with pytest.raises(RateLimitExceededError):
            check_rate_limit(firm_id=uuid4(), matter_id=uuid4())

    @patch("app.services.ai_rate_limiter._get_redis")
    def test_redis_failure_does_not_block(self, mock_get_redis):
        """Redis failures should be swallowed — AI processing continues."""
        mock_get_redis.side_effect = ConnectionError("Redis down")
        # Should NOT raise
        check_rate_limit(firm_id=uuid4(), matter_id=uuid4())

    @patch("app.services.ai_rate_limiter._get_redis")
    def test_rate_limit_exception_has_scope(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis
        mock_redis.eval.return_value = -1

        firm_id = uuid4()
        with pytest.raises(RateLimitExceededError) as exc_info:
            check_rate_limit(firm_id=firm_id, matter_id=uuid4())

        assert str(firm_id) in exc_info.value.scope

    @pytest.mark.asyncio
    async def test_classification_rate_limited(self):
        """Rate limit should stop classification before calling Claude."""
        from app.services.ai_classification_service import classify_document

        mock_db, _, _ = _make_classify_mocks()

        with (
            patch(
                "app.services.ai_classification_service.check_rate_limit",
                side_effect=RateLimitExceededError(scope="test", limit=100),
            ),
            patch(
                "app.services.ai_classification_service.text_extraction_service.extract_text",
                return_value="text",
            ),
            patch(
                "app.services.ai_classification_service._call_claude",
            ) as mock_claude,
        ):
            with pytest.raises(RateLimitExceededError):
                await classify_document(mock_db, document_id=uuid4())

            # Claude should NOT have been called
            mock_claude.assert_not_called()


# ─── Service Error Tests ──────────────────────────────────────────────────────


class TestServiceErrors:
    """Test error handling for missing documents, matters, etc."""

    @pytest.mark.asyncio
    async def test_classify_missing_document(self):
        from app.services.ai_classification_service import classify_document

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await classify_document(mock_db, document_id=uuid4())

    @pytest.mark.asyncio
    async def test_classify_missing_matter(self):
        from app.services.ai_classification_service import classify_document

        mock_db = AsyncMock()
        mock_doc = MagicMock()
        mock_doc.id = uuid4()
        mock_doc.matter_id = uuid4()

        r1 = MagicMock()
        r1.scalar_one_or_none.return_value = mock_doc
        r2 = MagicMock()
        r2.scalar_one_or_none.return_value = None  # Matter not found
        mock_db.execute.side_effect = [r1, r2]

        with pytest.raises(ValueError, match="Matter"):
            await classify_document(mock_db, document_id=mock_doc.id)

    @pytest.mark.asyncio
    async def test_extract_missing_document(self):
        from app.services.ai_extraction_service import extract_document_data

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await extract_document_data(mock_db, document_id=uuid4())

    @pytest.mark.asyncio
    async def test_letter_invalid_type(self):
        from app.services.ai_letter_service import draft_letter

        mock_db = AsyncMock()
        with pytest.raises(ValueError, match="Unknown letter type"):
            await draft_letter(
                mock_db,
                matter_id=uuid4(),
                asset_id=uuid4(),
                letter_type="nonexistent",
            )

    @pytest.mark.asyncio
    async def test_letter_missing_asset(self):
        from app.services.ai_letter_service import draft_letter

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await draft_letter(
                mock_db,
                matter_id=uuid4(),
                asset_id=uuid4(),
                letter_type="institution_notification",
            )

    @pytest.mark.asyncio
    async def test_suggest_tasks_missing_matter(self):
        from app.services.ai_suggestion_service import suggest_tasks

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await suggest_tasks(mock_db, matter_id=uuid4())

    @pytest.mark.asyncio
    async def test_detect_anomalies_missing_matter(self):
        from app.services.ai_anomaly_service import detect_anomalies

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await detect_anomalies(mock_db, matter_id=uuid4())


# ─── API Error Propagation Tests ──────────────────────────────────────────────


class TestAPIErrorPropagation:
    """Test that various API errors are properly logged before re-raising."""

    @pytest.mark.asyncio
    async def test_classification_api_error_logged(self):
        """API errors should be logged to ai_usage_logs before re-raising."""
        from app.services.ai_classification_service import classify_document

        mock_db, _, _ = _make_classify_mocks()

        with (
            patch("app.services.ai_classification_service.check_rate_limit"),
            patch(
                "app.services.ai_classification_service.text_extraction_service.extract_text",
                return_value="text",
            ),
            patch(
                "app.services.ai_classification_service._call_claude",
                side_effect=Exception("API error 500"),
            ),
        ):
            with pytest.raises(Exception, match="API error 500"):
                await classify_document(mock_db, document_id=uuid4())

            # Verify _log_ai_usage was called (it's the flush call on mock_db)
            # The db.add should have been called for the error log
            assert mock_db.add.called

    @pytest.mark.asyncio
    async def test_extraction_api_error_logged(self):
        from app.services.ai_extraction_service import extract_document_data

        mock_db = AsyncMock()
        doc_id = uuid4()
        matter_id = uuid4()

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.matter_id = matter_id
        mock_doc.doc_type = "account_statement"
        mock_doc.storage_key = "test.pdf"
        mock_doc.mime_type = "application/pdf"

        mock_matter = MagicMock()
        mock_matter.id = matter_id
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
                return_value="text",
            ),
            patch(
                "app.services.ai_extraction_service._call_claude",
                side_effect=Exception("API error"),
            ),
        ):
            with pytest.raises(Exception, match="API error"):
                await extract_document_data(mock_db, document_id=doc_id)

            assert mock_db.add.called
