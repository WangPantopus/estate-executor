"""Unit tests for AI anomaly detection service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.ai import AIAnomalyResponse, Anomaly
from app.services.ai_anomaly_service import (
    _build_tool_schema,
    _build_user_prompt,
    _estimate_cost,
)


class TestBuildUserPrompt:
    """Test user prompt construction."""

    def test_includes_document_data(self):
        prompt = _build_user_prompt(
            documents_data=[
                {
                    "id": "doc-123",
                    "filename": "statement.pdf",
                    "doc_type": "account_statement",
                    "extracted_data": {"institution": "Chase", "balance": 50000},
                },
            ],
            assets_summary=[
                {"id": "asset-456", "title": "Chase Checking", "type": "bank_account", "institution": "Chase", "value": "$50,000"},
            ],
            existing_tasks=["File Probate Petition"],
            stakeholder_names=["Jane Doe"],
        )
        assert "Chase" in prompt
        assert "statement.pdf" in prompt
        assert "Jane Doe" in prompt

    def test_handles_empty_data(self):
        prompt = _build_user_prompt(
            documents_data=[],
            assets_summary=[],
            existing_tasks=[],
            stakeholder_names=[],
        )
        assert "no documents" in prompt.lower()
        assert "no assets" in prompt.lower()

    def test_includes_asset_ids(self):
        prompt = _build_user_prompt(
            documents_data=[],
            assets_summary=[
                {"id": "abc12345-xxxx", "title": "Test", "type": "bank_account", "institution": "Bank", "value": "$100"},
            ],
            existing_tasks=[],
            stakeholder_names=[],
        )
        assert "abc12345" in prompt


class TestBuildToolSchema:
    """Test tool-use schema construction."""

    def test_tool_name(self):
        schema = _build_tool_schema()
        assert schema["name"] == "report_anomalies"

    def test_anomalies_is_array(self):
        schema = _build_tool_schema()
        props = schema["input_schema"]["properties"]
        assert props["anomalies"]["type"] == "array"

    def test_anomaly_has_required_fields(self):
        schema = _build_tool_schema()
        item_props = schema["input_schema"]["properties"]["anomalies"]["items"]["properties"]
        assert "type" in item_props
        assert "description" in item_props
        assert "severity" in item_props
        assert "document_id" in item_props
        assert "asset_id" in item_props

    def test_type_has_valid_enum(self):
        schema = _build_tool_schema()
        types = schema["input_schema"]["properties"]["anomalies"]["items"]["properties"]["type"]["enum"]
        assert "missing_asset" in types
        assert "value_discrepancy" in types
        assert "missing_stakeholder" in types
        assert "missing_task" in types
        assert "data_inconsistency" in types

    def test_severity_enum(self):
        schema = _build_tool_schema()
        severities = schema["input_schema"]["properties"]["anomalies"]["items"]["properties"]["severity"]["enum"]
        assert set(severities) == {"high", "medium", "low"}


class TestEstimateCost:
    def test_zero(self):
        assert _estimate_cost(0, 0) == 0.0


class TestAIAnomalyResponse:
    def test_valid_response(self):
        resp = AIAnomalyResponse(
            anomalies=[
                Anomaly(
                    type="missing_asset",
                    description="Document mentions account at Fidelity, but no asset registered",
                    severity="high",
                    document_id=uuid4(),
                    asset_id=None,
                ),
                Anomaly(
                    type="value_discrepancy",
                    description="Statement shows $500K but asset registered as $50K",
                    severity="high",
                    document_id=uuid4(),
                    asset_id=uuid4(),
                ),
            ]
        )
        assert len(resp.anomalies) == 2
        assert resp.anomalies[0].type == "missing_asset"
        assert resp.anomalies[1].severity == "high"

    def test_empty_anomalies(self):
        resp = AIAnomalyResponse(anomalies=[])
        assert len(resp.anomalies) == 0


class TestDetectAnomaliesService:
    @pytest.mark.asyncio
    async def test_missing_matter_raises(self):
        from app.services.ai_anomaly_service import detect_anomalies

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await detect_anomalies(mock_db, matter_id=uuid4())

    @pytest.mark.asyncio
    async def test_empty_data_returns_empty(self):
        """When no docs and no assets exist, return empty anomalies."""
        from app.services.ai_anomaly_service import detect_anomalies

        mock_db = AsyncMock()
        matter_id = uuid4()
        firm_id = uuid4()

        mock_matter = MagicMock()
        mock_matter.id = matter_id
        mock_matter.firm_id = firm_id

        mock_matter_result = MagicMock()
        mock_matter_result.scalar_one_or_none.return_value = mock_matter
        mock_docs_result = MagicMock()
        mock_docs_result.scalars.return_value.all.return_value = []
        mock_assets_result = MagicMock()
        mock_assets_result.scalars.return_value.all.return_value = []
        mock_tasks_result = MagicMock()
        mock_tasks_result.all.return_value = []
        mock_stakeholders_result = MagicMock()
        mock_stakeholders_result.all.return_value = []

        mock_db.execute.side_effect = [
            mock_matter_result,
            mock_docs_result,
            mock_assets_result,
            mock_tasks_result,
            mock_stakeholders_result,
        ]

        with patch("app.services.ai_anomaly_service.check_rate_limit"):
            result = await detect_anomalies(mock_db, matter_id=matter_id)

        assert len(result.anomalies) == 0

    @pytest.mark.asyncio
    async def test_successful_anomaly_detection(self):
        from app.services.ai_anomaly_service import detect_anomalies

        mock_db = AsyncMock()
        matter_id = uuid4()
        firm_id = uuid4()
        doc_id = uuid4()

        mock_matter = MagicMock()
        mock_matter.id = matter_id
        mock_matter.firm_id = firm_id

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.filename = "fidelity_statement.pdf"
        mock_doc.doc_type = "account_statement"
        mock_doc.ai_extracted_data = {
            "institution": "Fidelity",
            "balance": 500000,
            "account_type": "brokerage",
            "_extraction_metadata": {"model": "test"},
        }

        mock_matter_result = MagicMock()
        mock_matter_result.scalar_one_or_none.return_value = mock_matter
        mock_docs_result = MagicMock()
        mock_docs_result.scalars.return_value.all.return_value = [mock_doc]
        mock_assets_result = MagicMock()
        mock_assets_result.scalars.return_value.all.return_value = []
        mock_tasks_result = MagicMock()
        mock_tasks_result.all.return_value = []
        mock_stakeholders_result = MagicMock()
        mock_stakeholders_result.all.return_value = []

        mock_db.execute.side_effect = [
            mock_matter_result,
            mock_docs_result,
            mock_assets_result,
            mock_tasks_result,
            mock_stakeholders_result,
        ]

        claude_result = {
            "anomalies": [
                {
                    "type": "missing_asset",
                    "description": "Document mentions a Fidelity brokerage account with $500,000 balance, but no corresponding asset is registered",
                    "document_id": str(doc_id),
                    "asset_id": None,
                    "severity": "high",
                },
            ]
        }

        with (
            patch("app.services.ai_anomaly_service.check_rate_limit"),
            patch(
                "app.services.ai_anomaly_service._call_claude",
                return_value=(claude_result, 600, 200),
            ),
            patch(
                "app.services.ai_anomaly_service.event_logger.log",
                new_callable=AsyncMock,
            ),
        ):
            result = await detect_anomalies(mock_db, matter_id=matter_id)

        assert len(result.anomalies) == 1
        assert result.anomalies[0].type == "missing_asset"
        assert result.anomalies[0].severity == "high"
        assert "Fidelity" in result.anomalies[0].description


class TestAPIRouteExists:
    def test_detect_anomalies_endpoint(self):
        from pathlib import Path

        route_file = Path(__file__).parents[2] / "app" / "api" / "v1" / "ai" / "__init__.py"
        source = route_file.read_text()
        assert "detect-anomalies" in source
        assert "AIAnomalyResponse" in source
