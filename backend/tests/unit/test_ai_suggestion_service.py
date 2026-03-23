"""Unit tests for AI task suggestion service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.ai import AISuggestTasksResponse, TaskSuggestion
from app.services.ai_suggestion_service import (
    _build_tool_schema,
    _build_user_prompt,
    _estimate_cost,
)


class TestBuildUserPrompt:
    """Test user prompt construction."""

    def test_includes_decedent_name(self):
        prompt = _build_user_prompt(
            decedent_name="John Doe",
            estate_type="Testate Probate",
            jurisdiction="CA",
            phase="administration",
            assets_summary=[
                {"title": "Chase Checking", "type": "bank_account", "institution": "Chase", "value": "$50,000"},
            ],
            existing_tasks=["Obtain Death Certificate", "File Probate Petition"],
            entities_summary=[{"name": "Doe Family Trust", "type": "revocable_trust"}],
            stakeholder_roles=["matter_admin", "executor_trustee"],
            document_types=["death_certificate", "will"],
        )
        assert "John Doe" in prompt
        assert "Chase Checking" in prompt
        assert "Doe Family Trust" in prompt
        assert "Obtain Death Certificate" in prompt

    def test_handles_empty_data(self):
        prompt = _build_user_prompt(
            decedent_name="Jane Smith",
            estate_type="Intestate",
            jurisdiction="NY",
            phase="immediate",
            assets_summary=[],
            existing_tasks=[],
            entities_summary=[],
            stakeholder_roles=[],
            document_types=[],
        )
        assert "Jane Smith" in prompt
        assert "no assets registered" in prompt.lower()

    def test_includes_jurisdiction(self):
        prompt = _build_user_prompt(
            decedent_name="Test",
            estate_type="Probate",
            jurisdiction="TX",
            phase="immediate",
            assets_summary=[],
            existing_tasks=[],
            entities_summary=[],
            stakeholder_roles=[],
            document_types=[],
        )
        assert "TX" in prompt


class TestBuildToolSchema:
    """Test tool-use schema construction."""

    def test_tool_name(self):
        schema = _build_tool_schema()
        assert schema["name"] == "suggest_tasks"

    def test_suggestions_is_array(self):
        schema = _build_tool_schema()
        props = schema["input_schema"]["properties"]
        assert props["suggestions"]["type"] == "array"

    def test_suggestion_items_have_required_fields(self):
        schema = _build_tool_schema()
        item_props = schema["input_schema"]["properties"]["suggestions"]["items"]["properties"]
        assert "title" in item_props
        assert "description" in item_props
        assert "phase" in item_props
        assert "reasoning" in item_props

    def test_phase_has_valid_enum(self):
        schema = _build_tool_schema()
        phases = schema["input_schema"]["properties"]["suggestions"]["items"]["properties"]["phase"]["enum"]
        assert "immediate" in phases
        assert "tax" in phases
        assert "custom" in phases


class TestEstimateCost:
    def test_zero(self):
        assert _estimate_cost(0, 0) == 0.0

    def test_known(self):
        assert _estimate_cost(1_000_000, 1_000_000) == 18.0


class TestAISuggestTasksResponse:
    def test_valid_response(self):
        resp = AISuggestTasksResponse(
            suggestions=[
                TaskSuggestion(
                    title="Get business valuation",
                    description="Hire appraiser for the LLC",
                    phase="asset_inventory",
                    reasoning="Estate has a business interest",
                ),
            ]
        )
        assert len(resp.suggestions) == 1
        assert resp.suggestions[0].title == "Get business valuation"

    def test_empty_suggestions(self):
        resp = AISuggestTasksResponse(suggestions=[])
        assert len(resp.suggestions) == 0


class TestSuggestTasksService:
    @pytest.mark.asyncio
    async def test_missing_matter_raises(self):
        from app.services.ai_suggestion_service import suggest_tasks

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await suggest_tasks(mock_db, matter_id=uuid4())

    @pytest.mark.asyncio
    async def test_successful_suggestion(self):
        from app.services.ai_suggestion_service import suggest_tasks

        mock_db = AsyncMock()
        matter_id = uuid4()
        firm_id = uuid4()

        mock_matter = MagicMock()
        mock_matter.id = matter_id
        mock_matter.firm_id = firm_id
        mock_matter.decedent_name = "John Doe"
        mock_matter.estate_type = MagicMock(value="testate_probate")
        mock_matter.jurisdiction_state = "CA"
        mock_matter.phase = MagicMock(value="administration")

        # Mock all DB queries: matter, assets, tasks, entities, stakeholders, documents
        mock_matter_result = MagicMock()
        mock_matter_result.scalar_one_or_none.return_value = mock_matter
        mock_assets_result = MagicMock()
        mock_assets_result.scalars.return_value.all.return_value = []
        mock_tasks_result = MagicMock()
        mock_tasks_result.all.return_value = []
        mock_entities_result = MagicMock()
        mock_entities_result.scalars.return_value.all.return_value = []
        mock_stakeholders_result = MagicMock()
        mock_stakeholders_result.all.return_value = []
        mock_docs_result = MagicMock()
        mock_docs_result.all.return_value = []

        mock_db.execute.side_effect = [
            mock_matter_result,
            mock_assets_result,
            mock_tasks_result,
            mock_entities_result,
            mock_stakeholders_result,
            mock_docs_result,
        ]

        claude_result = {
            "suggestions": [
                {
                    "title": "Review digital asset access",
                    "description": "Secure access to online accounts",
                    "phase": "asset_inventory",
                    "reasoning": "Digital assets may exist but none are registered",
                },
            ]
        }

        with (
            patch("app.services.ai_suggestion_service.check_rate_limit"),
            patch(
                "app.services.ai_suggestion_service._call_claude",
                return_value=(claude_result, 500, 300),
            ),
            patch(
                "app.services.ai_suggestion_service.event_logger.log",
                new_callable=AsyncMock,
            ),
        ):
            result = await suggest_tasks(mock_db, matter_id=matter_id)

        assert len(result.suggestions) == 1
        assert result.suggestions[0].title == "Review digital asset access"


class TestAPIRouteExists:
    def test_suggest_tasks_endpoint(self):
        from pathlib import Path

        route_file = Path(__file__).parents[2] / "app" / "api" / "v1" / "ai" / "__init__.py"
        source = route_file.read_text()
        assert "suggest-tasks" in source
