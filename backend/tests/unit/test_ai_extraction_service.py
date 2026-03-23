"""Unit tests for AI extraction service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.ai import AIExtractResponse
from app.services.ai_extraction_service import (
    EXTRACTABLE_TYPES,
    EXTRACTION_SCHEMAS,
    _build_extraction_prompt,
    _build_extraction_tool,
    _estimate_cost,
)


class TestExtractionSchemas:
    """Verify per-type extraction schemas."""

    def test_all_6_types_defined(self):
        assert len(EXTRACTION_SCHEMAS) == 6

    def test_required_types_present(self):
        expected = {
            "account_statement",
            "deed",
            "insurance_policy",
            "trust_document",
            "appraisal",
            "tax_return",
        }
        assert set(EXTRACTION_SCHEMAS.keys()) == expected

    def test_extractable_types_matches(self):
        assert EXTRACTABLE_TYPES == set(EXTRACTION_SCHEMAS.keys())

    def test_account_statement_fields(self):
        schema = EXTRACTION_SCHEMAS["account_statement"]
        assert "institution" in schema["properties"]
        assert "account_type" in schema["properties"]
        assert "account_number_last4" in schema["properties"]
        assert "balance" in schema["properties"]
        assert "as_of_date" in schema["properties"]

    def test_deed_fields(self):
        schema = EXTRACTION_SCHEMAS["deed"]
        assert "property_address" in schema["properties"]
        assert "grantee" in schema["properties"]
        assert "recording_date" in schema["properties"]
        assert "parcel_number" in schema["properties"]
        assert "property_type" in schema["properties"]

    def test_insurance_policy_fields(self):
        schema = EXTRACTION_SCHEMAS["insurance_policy"]
        assert "carrier" in schema["properties"]
        assert "policy_number" in schema["properties"]
        assert "face_value" in schema["properties"]
        assert "beneficiary_name" in schema["properties"]
        assert "policy_type" in schema["properties"]

    def test_trust_document_fields(self):
        schema = EXTRACTION_SCHEMAS["trust_document"]
        assert "trust_name" in schema["properties"]
        assert "trust_type" in schema["properties"]
        assert "trustee" in schema["properties"]
        assert "successor_trustee" in schema["properties"]
        assert "date_established" in schema["properties"]
        assert "distribution_provisions" in schema["properties"]
        assert "special_provisions" in schema["properties"]
        assert "spendthrift_clause" in schema["properties"]
        assert "special_needs_provisions" in schema["properties"]

    def test_appraisal_fields(self):
        schema = EXTRACTION_SCHEMAS["appraisal"]
        assert "property_description" in schema["properties"]
        assert "appraised_value" in schema["properties"]
        assert "appraisal_date" in schema["properties"]
        assert "appraiser_name" in schema["properties"]

    def test_tax_return_fields(self):
        schema = EXTRACTION_SCHEMAS["tax_return"]
        assert "tax_year" in schema["properties"]
        assert "return_type" in schema["properties"]
        assert "gross_income" in schema["properties"]
        assert "tax_liability" in schema["properties"]


class TestBuildExtractionTool:
    """Test tool-use schema construction."""

    def test_tool_name(self):
        tool = _build_extraction_tool("account_statement")
        assert tool["name"] == "extract_data"

    def test_has_extracted_fields_and_confidence(self):
        tool = _build_extraction_tool("deed")
        props = tool["input_schema"]["properties"]
        assert "extracted_fields" in props
        assert "confidence" in props

    def test_all_types_build_valid_tool(self):
        for doc_type in EXTRACTION_SCHEMAS:
            tool = _build_extraction_tool(doc_type)
            assert tool["name"] == "extract_data"
            assert "input_schema" in tool
            assert "properties" in tool["input_schema"]

    def test_null_allowed_in_fields(self):
        """Fields should allow null values for missing data."""
        tool = _build_extraction_tool("account_statement")
        fields = tool["input_schema"]["properties"]["extracted_fields"]["properties"]
        # String/number fields should allow null
        assert "null" in str(fields["institution"]["type"])
        assert "null" in str(fields["balance"]["type"])


class TestBuildExtractionPrompt:
    """Test prompt construction."""

    def test_includes_document_text(self):
        system, user = _build_extraction_prompt("Test text here", "account_statement")
        assert "Test text here" in user
        assert "<document_text>" in user

    def test_system_mentions_doc_type(self):
        system, user = _build_extraction_prompt("text", "deed")
        assert "deed" in system

    def test_includes_null_instruction(self):
        system, user = _build_extraction_prompt("text", "insurance_policy")
        assert "null" in user.lower()

    def test_lists_expected_fields(self):
        system, user = _build_extraction_prompt("text", "tax_return")
        assert "tax_year" in user
        assert "return_type" in user


class TestEstimateCost:
    """Test cost estimation."""

    def test_zero_tokens_zero_cost(self):
        assert _estimate_cost(0, 0) == 0.0

    def test_known_values(self):
        cost = _estimate_cost(1_000_000, 1_000_000)
        assert cost == 18.0


class TestAIExtractResponse:
    """Test the response schema."""

    def test_valid_response(self):
        resp = AIExtractResponse(
            extracted_fields={"institution": "Chase Bank", "balance": 50000.00},
            confidence=0.9,
        )
        assert resp.extracted_fields["institution"] == "Chase Bank"
        assert resp.confidence == 0.9

    def test_empty_fields(self):
        resp = AIExtractResponse(extracted_fields={}, confidence=0.0)
        assert len(resp.extracted_fields) == 0

    def test_confidence_range(self):
        with pytest.raises(Exception):
            AIExtractResponse(extracted_fields={}, confidence=1.5)


class TestExtractDocumentDataService:
    """Test the main extract_document_data service function."""

    @pytest.mark.asyncio
    async def test_missing_document_raises(self):
        from app.services.ai_extraction_service import extract_document_data

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await extract_document_data(mock_db, document_id=uuid4())

    @pytest.mark.asyncio
    async def test_unclassified_document_raises(self):
        from app.services.ai_extraction_service import extract_document_data

        mock_db = AsyncMock()
        mock_doc = MagicMock()
        mock_doc.id = uuid4()
        mock_doc.doc_type = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not been classified"):
            await extract_document_data(mock_db, document_id=mock_doc.id)

    @pytest.mark.asyncio
    async def test_unsupported_type_raises(self):
        from app.services.ai_extraction_service import extract_document_data

        mock_db = AsyncMock()
        mock_doc = MagicMock()
        mock_doc.id = uuid4()
        mock_doc.doc_type = "death_certificate"  # Not extractable

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="does not support extraction"):
            await extract_document_data(mock_db, document_id=mock_doc.id)

    @pytest.mark.asyncio
    async def test_empty_text_returns_empty_fields(self):
        from app.services.ai_extraction_service import extract_document_data

        mock_db = AsyncMock()

        doc_id = uuid4()
        matter_id = uuid4()
        firm_id = uuid4()

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.matter_id = matter_id
        mock_doc.storage_key = "test/key.pdf"
        mock_doc.mime_type = "application/pdf"
        mock_doc.doc_type = "account_statement"

        mock_matter = MagicMock()
        mock_matter.id = matter_id
        mock_matter.firm_id = firm_id

        mock_result_doc = MagicMock()
        mock_result_doc.scalar_one_or_none.return_value = mock_doc
        mock_result_matter = MagicMock()
        mock_result_matter.scalar_one_or_none.return_value = mock_matter
        mock_db.execute.side_effect = [mock_result_doc, mock_result_matter]

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

    @pytest.mark.asyncio
    async def test_successful_extraction(self):
        from app.services.ai_extraction_service import extract_document_data

        mock_db = AsyncMock()

        doc_id = uuid4()
        matter_id = uuid4()
        firm_id = uuid4()

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.matter_id = matter_id
        mock_doc.storage_key = "test/key.pdf"
        mock_doc.mime_type = "application/pdf"
        mock_doc.doc_type = "account_statement"
        mock_doc.ai_extracted_data = None

        mock_matter = MagicMock()
        mock_matter.id = matter_id
        mock_matter.firm_id = firm_id

        mock_result_doc = MagicMock()
        mock_result_doc.scalar_one_or_none.return_value = mock_doc
        mock_result_matter = MagicMock()
        mock_result_matter.scalar_one_or_none.return_value = mock_matter
        mock_db.execute.side_effect = [mock_result_doc, mock_result_matter]

        claude_result = {
            "extracted_fields": {
                "institution": "Chase Bank",
                "account_type": "checking",
                "account_number_last4": "1234",
                "balance": 50000.00,
                "as_of_date": "2025-12-31",
            },
            "confidence": 0.92,
        }

        with (
            patch("app.services.ai_extraction_service.check_rate_limit"),
            patch(
                "app.services.ai_extraction_service.text_extraction_service.extract_text",
                return_value="CHASE BANK\nAccount Statement\nChecking ****1234\nBalance: $50,000.00",
            ),
            patch(
                "app.services.ai_extraction_service._call_claude",
                return_value=(claude_result, 600, 150),
            ),
            patch(
                "app.services.ai_extraction_service.event_logger.log",
                new_callable=AsyncMock,
            ) as mock_event_log,
        ):
            result = await extract_document_data(mock_db, document_id=doc_id)

        assert result.extracted_fields["institution"] == "Chase Bank"
        assert result.extracted_fields["balance"] == 50000.00
        assert result.confidence == 0.92

        # Verify document was updated with extracted data
        assert mock_doc.ai_extracted_data is not None
        assert mock_doc.ai_extracted_data["institution"] == "Chase Bank"
        assert "_extraction_metadata" in mock_doc.ai_extracted_data

        # Verify event was logged
        mock_event_log.assert_called_once()
        call_kwargs = mock_event_log.call_args.kwargs
        assert call_kwargs["action"] == "data_extracted"
        assert call_kwargs["actor_type"].value == "ai"

    @pytest.mark.asyncio
    async def test_null_fields_preserved(self):
        """Fields that are null should stay null (not hallucinated)."""
        from app.services.ai_extraction_service import extract_document_data

        mock_db = AsyncMock()

        doc_id = uuid4()
        matter_id = uuid4()
        firm_id = uuid4()

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.matter_id = matter_id
        mock_doc.storage_key = "test/key.pdf"
        mock_doc.mime_type = "application/pdf"
        mock_doc.doc_type = "insurance_policy"
        mock_doc.ai_extracted_data = None

        mock_matter = MagicMock()
        mock_matter.id = matter_id
        mock_matter.firm_id = firm_id

        mock_result_doc = MagicMock()
        mock_result_doc.scalar_one_or_none.return_value = mock_doc
        mock_result_matter = MagicMock()
        mock_result_matter.scalar_one_or_none.return_value = mock_matter
        mock_db.execute.side_effect = [mock_result_doc, mock_result_matter]

        claude_result = {
            "extracted_fields": {
                "carrier": "Prudential",
                "policy_number": "POL-12345",
                "face_value": 500000.00,
                "beneficiary_name": None,  # Not found in doc
                "policy_type": "whole",
            },
            "confidence": 0.85,
        }

        with (
            patch("app.services.ai_extraction_service.check_rate_limit"),
            patch(
                "app.services.ai_extraction_service.text_extraction_service.extract_text",
                return_value="Prudential Insurance Policy POL-12345",
            ),
            patch(
                "app.services.ai_extraction_service._call_claude",
                return_value=(claude_result, 500, 100),
            ),
            patch(
                "app.services.ai_extraction_service.event_logger.log",
                new_callable=AsyncMock,
            ),
        ):
            result = await extract_document_data(mock_db, document_id=doc_id)

        assert result.extracted_fields["carrier"] == "Prudential"
        assert result.extracted_fields["beneficiary_name"] is None
        assert result.extracted_fields["face_value"] == 500000.00


class TestAutoExtractionThreshold:
    """Verify the auto-extraction threshold constant."""

    def test_threshold_is_0_7(self):
        from app.workers.ai_tasks import _AUTO_EXTRACT_CONFIDENCE_THRESHOLD

        assert _AUTO_EXTRACT_CONFIDENCE_THRESHOLD == 0.7


class TestExtractionChaining:
    """Verify extraction is chained after classification."""

    def test_classify_document_task_exists(self):
        from app.workers.ai_tasks import classify_document

        assert callable(classify_document)

    def test_extract_document_data_task_exists(self):
        from app.workers.ai_tasks import extract_document_data

        assert callable(extract_document_data)

    def test_extract_task_name(self):
        from app.workers.ai_tasks import extract_document_data

        assert extract_document_data.name == "app.workers.ai_tasks.extract_document_data"


class TestAIRouteExists:
    """Verify the AI API route module exists."""

    def test_ai_route_module_importable(self):
        """AI route module should exist and define an extract endpoint."""
        import ast
        from pathlib import Path

        route_file = Path(__file__).parents[2] / "app" / "api" / "v1" / "ai" / "__init__.py"
        assert route_file.exists(), "AI route file should exist"

        source = route_file.read_text()
        assert "extract_document_data" in source
        assert "extract/{doc_id}" in source
        assert "AIExtractResponse" in source
