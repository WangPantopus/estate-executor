"""AI pipeline tests — extraction accuracy with sample documents.

Tests structured data extraction for each extractable doc type with
representative document text, verifying correct field extraction and null handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.ai_extraction_service import (
    EXTRACTABLE_TYPES,
    EXTRACTION_SCHEMAS,
    _build_extraction_prompt,
    _build_extraction_tool,
    extract_document_data,
)

# ─── Sample extraction results per doc type ───────────────────────────────────

EXTRACTION_SAMPLES: list[dict] = [
    {
        "doc_type": "account_statement",
        "text": "CHASE BANK\nChecking Account Statement\nAccount: ****4567\nBalance: $52,104.55\nAs of December 31, 2024",
        "expected_result": {
            "extracted_fields": {
                "institution": "Chase Bank",
                "account_type": "checking",
                "account_number_last4": "4567",
                "balance": 52104.55,
                "as_of_date": "2024-12-31",
            },
            "confidence": 0.95,
        },
        "label": "bank_statement_full_fields",
    },
    {
        "doc_type": "account_statement",
        "text": "FIDELITY INVESTMENTS\nBrokerage\nValue: $1,245,678.90\nDate: Dec 31, 2024",
        "expected_result": {
            "extracted_fields": {
                "institution": "Fidelity Investments",
                "account_type": "brokerage",
                "account_number_last4": None,
                "balance": 1245678.90,
                "as_of_date": "2024-12-31",
            },
            "confidence": 0.85,
        },
        "label": "brokerage_missing_account_number",
    },
    {
        "doc_type": "deed",
        "text": "GRANT DEED\nAPN: 1234-567-890\nProperty: 123 Main St, LA, CA\nGrantee: Doe Family Trust\nRecorded: January 20, 2020\nResidential",
        "expected_result": {
            "extracted_fields": {
                "property_address": "123 Main St, LA, CA",
                "grantee": "Doe Family Trust",
                "recording_date": "2020-01-20",
                "parcel_number": "1234-567-890",
                "property_type": "residential",
            },
            "confidence": 0.93,
        },
        "label": "grant_deed_all_fields",
    },
    {
        "doc_type": "insurance_policy",
        "text": "PRUDENTIAL\nWhole Life Policy PLI-2020-789456\nInsured: John Doe\nFace Value: $500,000\nBeneficiary: Jane Doe",
        "expected_result": {
            "extracted_fields": {
                "carrier": "Prudential",
                "policy_number": "PLI-2020-789456",
                "face_value": 500000.0,
                "beneficiary_name": "Jane Doe",
                "policy_type": "whole",
            },
            "confidence": 0.91,
        },
        "label": "whole_life_policy",
    },
    {
        "doc_type": "insurance_policy",
        "text": "NORTHWESTERN MUTUAL\nTerm Life Policy NM-456789\nDeath Benefit: $1,000,000\nInsured: John Doe",
        "expected_result": {
            "extracted_fields": {
                "carrier": "Northwestern Mutual",
                "policy_number": "NM-456789",
                "face_value": 1000000.0,
                "beneficiary_name": None,
                "policy_type": "term",
            },
            "confidence": 0.82,
        },
        "label": "term_life_missing_beneficiary",
    },
    {
        "doc_type": "trust_document",
        "text": "DOE FAMILY REVOCABLE TRUST\nTrustee: John Doe\nSuccessor: First National Bank\nEstablished: April 15, 2018\nDistribution: Equal shares to children\nSpendthrift clause included.",
        "expected_result": {
            "extracted_fields": {
                "trust_name": "Doe Family Revocable Trust",
                "trust_type": "revocable",
                "trustee": "John Doe",
                "successor_trustee": "First National Bank",
                "date_established": "2018-04-15",
                "distribution_provisions": "Equal shares to children",
                "special_provisions": [],
                "spendthrift_clause": True,
                "special_needs_provisions": False,
            },
            "confidence": 0.90,
        },
        "label": "revocable_trust_with_clauses",
    },
    {
        "doc_type": "appraisal",
        "text": "APPRAISAL REPORT\n123 Main St, LA, CA\nSingle Family Residence\nAppraised Value: $1,250,000\nDate: December 10, 2024\nAppraiser: James Wilson, MAI",
        "expected_result": {
            "extracted_fields": {
                "property_description": "123 Main St, LA, CA - Single Family Residence",
                "appraised_value": 1250000.0,
                "appraisal_date": "2024-12-10",
                "appraiser_name": "James Wilson",
            },
            "confidence": 0.94,
        },
        "label": "residential_appraisal",
    },
    {
        "doc_type": "tax_return",
        "text": "Form 1040 - 2024\nJohn Doe\nGross Income: $285,000\nTotal Tax: $52,340\nFiling Status: MFJ",
        "expected_result": {
            "extracted_fields": {
                "tax_year": 2024,
                "return_type": "1040",
                "gross_income": 285000.0,
                "tax_liability": 52340.0,
            },
            "confidence": 0.88,
        },
        "label": "form_1040",
    },
]


def _make_mock_db(doc_id, matter_id, firm_id, doc_type):
    """Create a mock DB with a classified document."""
    mock_db = AsyncMock()

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.matter_id = matter_id
    mock_doc.storage_key = "test/key.pdf"
    mock_doc.mime_type = "application/pdf"
    mock_doc.doc_type = doc_type
    mock_doc.ai_extracted_data = None

    mock_matter = MagicMock()
    mock_matter.id = matter_id
    mock_matter.firm_id = firm_id

    mock_result_doc = MagicMock()
    mock_result_doc.scalar_one_or_none.return_value = mock_doc
    mock_result_matter = MagicMock()
    mock_result_matter.scalar_one_or_none.return_value = mock_matter
    mock_db.execute.side_effect = [mock_result_doc, mock_result_matter]

    return mock_db, mock_doc


class TestExtractionAccuracy:
    """Test extraction with sample documents for each extractable type."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "sample",
        EXTRACTION_SAMPLES,
        ids=[s["label"] for s in EXTRACTION_SAMPLES],
    )
    async def test_extracts_fields_correctly(self, sample):
        doc_id = uuid4()
        matter_id = uuid4()
        firm_id = uuid4()
        mock_db, mock_doc = _make_mock_db(doc_id, matter_id, firm_id, sample["doc_type"])

        with (
            patch("app.services.ai_extraction_service.check_rate_limit"),
            patch(
                "app.services.ai_extraction_service.text_extraction_service.extract_text",
                return_value=sample["text"],
            ),
            patch(
                "app.services.ai_extraction_service._call_claude",
                return_value=(sample["expected_result"], 600, 200),
            ),
            patch(
                "app.services.ai_extraction_service.event_logger.log",
                new_callable=AsyncMock,
            ),
        ):
            result = await extract_document_data(mock_db, document_id=doc_id)

        expected_fields = sample["expected_result"]["extracted_fields"]
        for field_name, expected_value in expected_fields.items():
            assert field_name in result.extracted_fields, f"Missing field: {field_name}"
            assert result.extracted_fields[field_name] == expected_value, (
                f"Field {field_name}: expected {expected_value}, got {result.extracted_fields[field_name]}"
            )

    def test_all_extractable_types_covered(self):
        """All extractable doc types should have at least one test sample."""
        covered = {s["doc_type"] for s in EXTRACTION_SAMPLES}
        assert covered == EXTRACTABLE_TYPES


class TestExtractionNullHandling:
    """Test that null/missing fields are handled correctly."""

    @pytest.mark.asyncio
    async def test_null_fields_preserved(self):
        """Fields that Claude returns as null should remain null."""
        doc_id = uuid4()
        matter_id = uuid4()
        firm_id = uuid4()
        mock_db, _ = _make_mock_db(doc_id, matter_id, firm_id, "insurance_policy")

        claude_result = {
            "extracted_fields": {
                "carrier": "Unknown Carrier",
                "policy_number": None,
                "face_value": None,
                "beneficiary_name": None,
                "policy_type": "other",
            },
            "confidence": 0.45,
        }

        with (
            patch("app.services.ai_extraction_service.check_rate_limit"),
            patch(
                "app.services.ai_extraction_service.text_extraction_service.extract_text",
                return_value="Some unclear insurance document",
            ),
            patch(
                "app.services.ai_extraction_service._call_claude",
                return_value=(claude_result, 400, 150),
            ),
            patch(
                "app.services.ai_extraction_service.event_logger.log",
                new_callable=AsyncMock,
            ),
        ):
            result = await extract_document_data(mock_db, document_id=doc_id)

        assert result.extracted_fields["policy_number"] is None
        assert result.extracted_fields["face_value"] is None
        assert result.extracted_fields["beneficiary_name"] is None
        assert result.extracted_fields["carrier"] == "Unknown Carrier"

    @pytest.mark.asyncio
    async def test_empty_text_returns_empty_fields(self):
        """When text extraction fails, return empty fields."""
        doc_id = uuid4()
        matter_id = uuid4()
        firm_id = uuid4()
        mock_db, _ = _make_mock_db(doc_id, matter_id, firm_id, "account_statement")

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


class TestExtractionToolSchemas:
    """Validate tool schemas for each extractable type."""

    @pytest.mark.parametrize("doc_type", sorted(EXTRACTABLE_TYPES))
    def test_tool_schema_valid(self, doc_type):
        tool = _build_extraction_tool(doc_type)
        assert tool["name"] == "extract_data"
        assert "input_schema" in tool
        fields_schema = tool["input_schema"]["properties"]["extracted_fields"]
        assert "properties" in fields_schema

        # All fields from EXTRACTION_SCHEMAS should be present
        expected_fields = set(EXTRACTION_SCHEMAS[doc_type]["properties"].keys())
        actual_fields = set(fields_schema["properties"].keys())
        assert actual_fields == expected_fields

    @pytest.mark.parametrize("doc_type", sorted(EXTRACTABLE_TYPES))
    def test_prompt_includes_fields(self, doc_type):
        system, user = _build_extraction_prompt("test text", doc_type)
        for field_name in EXTRACTION_SCHEMAS[doc_type]["properties"]:
            assert field_name in user


class TestExtractionDocTypeValidation:
    """Test that non-extractable doc types are rejected."""

    @pytest.mark.asyncio
    async def test_unclassified_document_rejected(self):
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
    @pytest.mark.parametrize(
        "doc_type", ["death_certificate", "will", "court_filing", "correspondence", "other"]
    )
    async def test_non_extractable_types_rejected(self, doc_type):
        mock_db = AsyncMock()
        mock_doc = MagicMock()
        mock_doc.id = uuid4()
        mock_doc.doc_type = doc_type
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="does not support extraction"):
            await extract_document_data(mock_db, document_id=mock_doc.id)
