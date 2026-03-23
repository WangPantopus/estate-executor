"""Unit tests for AI trust analysis service and entity map enhancements."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.enums import EntityType, FundingStatus
from app.services.ai_trust_analysis_service import (
    _build_tool_schema,
    _build_user_prompt,
    _estimate_cost,
    _resolve_trust_type,
)


class TestResolveTrustType:
    """Test trust type string to enum mapping."""

    def test_revocable(self):
        assert _resolve_trust_type("revocable") == EntityType.revocable_trust

    def test_revocable_trust(self):
        assert _resolve_trust_type("revocable trust") == EntityType.revocable_trust

    def test_living_trust(self):
        assert _resolve_trust_type("living trust") == EntityType.revocable_trust

    def test_irrevocable(self):
        assert _resolve_trust_type("irrevocable") == EntityType.irrevocable_trust

    def test_special_needs(self):
        assert _resolve_trust_type("special needs trust") == EntityType.irrevocable_trust

    def test_unknown_defaults_to_revocable(self):
        assert _resolve_trust_type("unknown type") == EntityType.revocable_trust

    def test_none_defaults_to_revocable(self):
        assert _resolve_trust_type(None) == EntityType.revocable_trust

    def test_case_insensitive(self):
        assert _resolve_trust_type("REVOCABLE TRUST") == EntityType.revocable_trust
        assert _resolve_trust_type("Irrevocable") == EntityType.irrevocable_trust


class TestBuildUserPrompt:
    def test_includes_trust_data(self):
        prompt = _build_user_prompt(
            trust_data={"trust_name": "Doe Trust", "trustee": "Jane Doe"},
            assets_summary=[
                {"id": "abc123", "title": "House", "type": "real_estate", "institution": "N/A", "value": "$500,000", "transfer_mechanism": "probate"},
            ],
        )
        assert "Doe Trust" in prompt
        assert "Jane Doe" in prompt
        assert "House" in prompt

    def test_handles_empty_data(self):
        prompt = _build_user_prompt(
            trust_data={},
            assets_summary=[],
        )
        assert "no extracted fields" in prompt.lower()
        assert "no assets registered" in prompt.lower()


class TestBuildToolSchema:
    def test_tool_name(self):
        schema = _build_tool_schema()
        assert schema["name"] == "analyze_trust_funding"

    def test_has_funding_suggestions(self):
        schema = _build_tool_schema()
        props = schema["input_schema"]["properties"]
        assert "funding_suggestions" in props
        assert props["funding_suggestions"]["type"] == "array"

    def test_has_missing_assets(self):
        schema = _build_tool_schema()
        props = schema["input_schema"]["properties"]
        assert "missing_assets" in props
        assert props["missing_assets"]["type"] == "array"


class TestEstimateCost:
    def test_zero(self):
        assert _estimate_cost(0, 0) == 0.0


class TestAnalyzeTrustDocument:
    @pytest.mark.asyncio
    async def test_non_trust_document_raises(self):
        from app.services.ai_trust_analysis_service import analyze_trust_document

        mock_db = AsyncMock()
        mock_doc = MagicMock()
        mock_doc.doc_type = "account_statement"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not a trust document"):
            await analyze_trust_document(mock_db, document_id=uuid4(), matter_id=uuid4())

    @pytest.mark.asyncio
    async def test_missing_document_raises(self):
        from app.services.ai_trust_analysis_service import analyze_trust_document

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await analyze_trust_document(mock_db, document_id=uuid4(), matter_id=uuid4())

    @pytest.mark.asyncio
    async def test_successful_analysis_with_entity_creation(self):
        from app.services.ai_trust_analysis_service import analyze_trust_document

        mock_db = AsyncMock()
        doc_id = uuid4()
        matter_id = uuid4()
        firm_id = uuid4()

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.doc_type = "trust_document"
        mock_doc.matter_id = matter_id
        mock_doc.ai_extracted_data = {
            "trust_name": "Doe Family Trust",
            "trust_type": "revocable",
            "trustee": "Jane Doe",
            "successor_trustee": "First National Bank",
            "distribution_provisions": "Equal distribution among children",
            "spendthrift_clause": True,
            "special_needs_provisions": False,
            "_extraction_metadata": {},
        }

        mock_matter = MagicMock()
        mock_matter.id = matter_id
        mock_matter.firm_id = firm_id

        # No existing entity with same name
        mock_existing_entity = MagicMock()
        mock_existing_entity.scalar_one_or_none.return_value = None

        mock_doc_result = MagicMock()
        mock_doc_result.scalar_one_or_none.return_value = mock_doc
        mock_matter_result = MagicMock()
        mock_matter_result.scalar_one_or_none.return_value = mock_matter
        mock_assets_result = MagicMock()
        mock_assets_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [
            mock_doc_result,
            mock_matter_result,
            mock_existing_entity,
            mock_assets_result,
        ]

        claude_result = {
            "funding_suggestions": [],
            "missing_assets": [],
        }

        with (
            patch("app.services.ai_trust_analysis_service.check_rate_limit"),
            patch(
                "app.services.ai_trust_analysis_service._call_claude",
                return_value=(claude_result, 400, 200),
            ),
            patch(
                "app.services.ai_trust_analysis_service.event_logger.log",
                new_callable=AsyncMock,
            ),
        ):
            result = await analyze_trust_document(
                mock_db, document_id=doc_id, matter_id=matter_id
            )

        assert result["entity_created"] is True
        assert result["trust_name"] == "Doe Family Trust"
        # entity_id is None in mocked tests because db.flush() doesn't set the server-generated UUID
        assert "entity_id" in result


class TestEntityMapFundingSummary:
    """Test the enhanced entity map response with funding summary."""

    def test_funding_detail_schema(self):
        from app.schemas.entities import FundingDetail

        detail = FundingDetail(
            entity_id=uuid4(),
            entity_name="Test Trust",
            funding_status=FundingStatus.partially_funded,
            funded_count=3,
            total_value=150000.0,
        )
        assert detail.entity_name == "Test Trust"
        assert detail.funded_count == 3

    def test_entity_map_response_has_funding_summary(self):
        from app.schemas.entities import EntityMapResponse

        fields = EntityMapResponse.model_fields
        assert "funding_summary" in fields

    def test_entity_map_response_has_pour_over(self):
        from app.schemas.entities import EntityMapResponse

        fields = EntityMapResponse.model_fields
        assert "pour_over_candidates" in fields


class TestAPIRouteExists:
    def test_analyze_trust_endpoint(self):
        from pathlib import Path

        route_file = Path(__file__).parents[2] / "app" / "api" / "v1" / "ai" / "__init__.py"
        source = route_file.read_text()
        assert "analyze-trust" in source
        assert "analyze_trust_document" in source
