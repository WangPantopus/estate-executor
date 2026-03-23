"""Unit tests for AI classification service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.ai import AIClassifyResponse
from app.services.ai_classification_service import (
    _MODEL,
    DOCUMENT_TYPES,
    _build_classification_prompt,
    _build_tool_schema,
    _estimate_cost,
)


class TestDocumentTypes:
    """Verify document type definitions."""

    def test_all_11_types_defined(self):
        assert len(DOCUMENT_TYPES) == 11

    def test_required_types_present(self):
        expected = {
            "death_certificate",
            "will",
            "trust_document",
            "deed",
            "account_statement",
            "insurance_policy",
            "court_filing",
            "tax_return",
            "appraisal",
            "correspondence",
            "other",
        }
        assert set(DOCUMENT_TYPES.keys()) == expected

    def test_all_types_have_descriptions(self):
        for doc_type, desc in DOCUMENT_TYPES.items():
            assert isinstance(desc, str)
            assert len(desc) > 10, f"Description for {doc_type} is too short"


class TestModelConfig:
    """Verify Claude model configuration."""

    def test_model_is_sonnet(self):
        assert "sonnet" in _MODEL


class TestBuildClassificationPrompt:
    """Test prompt construction."""

    def test_includes_document_text(self):
        prompt = _build_classification_prompt("Here is some document text")
        assert "Here is some document text" in prompt
        assert "<document_text>" in prompt
        assert "</document_text>" in prompt

    def test_includes_all_document_types(self):
        prompt = _build_classification_prompt("test")
        for doc_type in DOCUMENT_TYPES:
            assert doc_type in prompt

    def test_includes_matter_context(self):
        prompt = _build_classification_prompt(
            "test",
            estate_type="testate_probate",
            jurisdiction="CA",
            decedent_name="John Smith",
        )
        assert "testate_probate" in prompt
        assert "CA" in prompt
        assert "John Smith" in prompt

    def test_omits_context_when_none(self):
        prompt = _build_classification_prompt("test")
        assert "Matter context:" not in prompt

    def test_partial_context(self):
        prompt = _build_classification_prompt("test", jurisdiction="NY")
        assert "NY" in prompt
        assert "Context:" in prompt


class TestBuildToolSchema:
    """Test tool schema for structured output."""

    def test_schema_has_required_fields(self):
        schema = _build_tool_schema()
        assert schema["name"] == "classify_document"
        props = schema["input_schema"]["properties"]
        assert "doc_type" in props
        assert "confidence" in props
        assert "reasoning" in props

    def test_doc_type_has_enum(self):
        schema = _build_tool_schema()
        enum_values = schema["input_schema"]["properties"]["doc_type"]["enum"]
        assert set(enum_values) == set(DOCUMENT_TYPES.keys())

    def test_confidence_has_range(self):
        schema = _build_tool_schema()
        confidence = schema["input_schema"]["properties"]["confidence"]
        assert confidence["minimum"] == 0.0
        assert confidence["maximum"] == 1.0

    def test_required_fields_specified(self):
        schema = _build_tool_schema()
        required = schema["input_schema"]["required"]
        assert "doc_type" in required
        assert "confidence" in required
        assert "reasoning" in required


class TestEstimateCost:
    """Test cost estimation."""

    def test_zero_tokens_zero_cost(self):
        assert _estimate_cost(0, 0) == 0.0

    def test_known_values(self):
        # 1M input tokens = $3.0, 1M output tokens = $15.0
        cost = _estimate_cost(1_000_000, 1_000_000)
        assert cost == 18.0

    def test_small_call(self):
        # 1000 input + 200 output
        cost = _estimate_cost(1000, 200)
        expected = (1000 / 1_000_000) * 3.0 + (200 / 1_000_000) * 15.0
        assert abs(cost - round(expected, 6)) < 0.000001

    def test_returns_float(self):
        assert isinstance(_estimate_cost(100, 50), float)


class TestAIClassifyResponse:
    """Test the response schema."""

    def test_valid_response(self):
        resp = AIClassifyResponse(
            doc_type="death_certificate",
            confidence=0.95,
            reasoning="Contains official death record fields",
        )
        assert resp.doc_type == "death_certificate"
        assert resp.confidence == 0.95

    def test_confidence_range_validation(self):
        with pytest.raises(ValidationError):
            AIClassifyResponse(
                doc_type="will",
                confidence=1.5,  # Over max
                reasoning="test",
            )

    def test_negative_confidence_rejected(self):
        with pytest.raises(ValidationError):
            AIClassifyResponse(
                doc_type="will",
                confidence=-0.1,
                reasoning="test",
            )


class TestClassifyDocumentService:
    """Test the main classify_document service function."""

    @pytest.mark.asyncio
    async def test_missing_document_raises(self):
        """Should raise ValueError if document not found."""
        from app.services.ai_classification_service import classify_document

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await classify_document(mock_db, document_id=uuid4())

    @pytest.mark.asyncio
    async def test_empty_text_returns_other(self):
        """Should return 'other' with 0.0 confidence when text extraction fails."""
        from app.services.ai_classification_service import classify_document

        mock_db = AsyncMock()

        # Mock document
        mock_doc = MagicMock()
        mock_doc.id = uuid4()
        mock_doc.matter_id = uuid4()
        mock_doc.storage_key = "test/key.pdf"
        mock_doc.mime_type = "application/pdf"

        # Mock matter
        mock_matter = MagicMock()
        mock_matter.id = mock_doc.matter_id
        mock_matter.firm_id = uuid4()
        mock_matter.estate_type = "testate_probate"
        mock_matter.jurisdiction_state = "CA"
        mock_matter.decedent_name = "John Doe"

        # First execute returns doc, second returns matter
        mock_result_doc = MagicMock()
        mock_result_doc.scalar_one_or_none.return_value = mock_doc
        mock_result_matter = MagicMock()
        mock_result_matter.scalar_one_or_none.return_value = mock_matter
        mock_db.execute.side_effect = [mock_result_doc, mock_result_matter]

        with (
            patch("app.services.ai_classification_service.check_rate_limit"),
            patch(
                "app.services.ai_classification_service.text_extraction_service.extract_text",
                return_value="",
            ),
        ):
            result = await classify_document(mock_db, document_id=mock_doc.id)

        assert result.doc_type == "other"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_successful_classification(self):
        """Full classification flow with mocked Claude API."""
        from app.services.ai_classification_service import classify_document

        mock_db = AsyncMock()

        doc_id = uuid4()
        matter_id = uuid4()
        firm_id = uuid4()

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
        mock_matter.estate_type = "testate_probate"
        mock_matter.jurisdiction_state = "CA"
        mock_matter.decedent_name = "John Doe"

        mock_result_doc = MagicMock()
        mock_result_doc.scalar_one_or_none.return_value = mock_doc
        mock_result_matter = MagicMock()
        mock_result_matter.scalar_one_or_none.return_value = mock_matter
        mock_db.execute.side_effect = [mock_result_doc, mock_result_matter]

        claude_result = {
            "doc_type": "death_certificate",
            "confidence": 0.95,
            "reasoning": "Contains official death record fields",
        }

        with (
            patch("app.services.ai_classification_service.check_rate_limit"),
            patch(
                "app.services.ai_classification_service.text_extraction_service.extract_text",
                return_value="CERTIFICATE OF DEATH\nState of California...",
            ),
            patch(
                "app.services.ai_classification_service._call_claude",
                return_value=(claude_result, 500, 100),
            ),
            patch(
                "app.services.ai_classification_service.event_logger.log",
                new_callable=AsyncMock,
            ) as mock_event_log,
        ):
            result = await classify_document(mock_db, document_id=doc_id)

        assert result.doc_type == "death_certificate"
        assert result.confidence == 0.95
        assert result.reasoning == "Contains official death record fields"

        # Verify document was updated
        assert mock_doc.doc_type == "death_certificate"
        assert mock_doc.doc_type_confidence == 0.95

        # Verify event was logged
        mock_event_log.assert_called_once()
        call_kwargs = mock_event_log.call_args.kwargs
        assert call_kwargs["actor_type"].value == "ai"
        assert call_kwargs["action"] == "classified"
        assert call_kwargs["entity_type"] == "document"
