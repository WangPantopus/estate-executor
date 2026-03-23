"""Unit tests for AI letter drafting service.

Note: imports are done inside test methods to avoid triggering the
jwt/cryptography import chain that fails in this test environment.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.ai import AILetterDraftResponse


class TestLetterTypes:
    """Verify letter type definitions."""

    def _get_types(self):
        # Import at call site to bypass the import chain
        with patch.dict("sys.modules", {}):
            from app.services.ai_letter_service import LETTER_TYPES
        return LETTER_TYPES

    def test_all_6_types_defined(self):
        from app.services.ai_letter_service import LETTER_TYPES

        assert len(LETTER_TYPES) == 6

    def test_required_types_present(self):
        from app.services.ai_letter_service import LETTER_TYPES

        expected = {
            "institution_notification",
            "creditor_notification",
            "beneficiary_notification",
            "government_agency",
            "subscription_cancellation",
            "insurance_claim",
        }
        assert set(LETTER_TYPES.keys()) == expected

    def test_all_types_have_label_and_description(self):
        from app.services.ai_letter_service import LETTER_TYPES

        for key, config in LETTER_TYPES.items():
            assert "label" in config, f"{key} missing label"
            assert "description" in config, f"{key} missing description"
            assert "purpose" in config, f"{key} missing purpose"
            assert len(config["label"]) > 5
            assert len(config["description"]) > 10


class TestSystemPrompt:
    """Verify system prompt content."""

    def test_mentions_estate_administration(self):
        from app.services.ai_letter_service import _build_system_prompt

        prompt = _build_system_prompt()
        assert "estate administration" in prompt

    def test_warns_about_sensitive_info(self):
        from app.services.ai_letter_service import _build_system_prompt

        prompt = _build_system_prompt()
        assert "Social Security" in prompt
        assert "account number" in prompt.lower()


class TestBuildUserPrompt:
    """Test user prompt construction."""

    def test_includes_decedent_name(self):
        from app.services.ai_letter_service import LETTER_TYPES, _build_user_prompt

        prompt = _build_user_prompt(
            letter_type="institution_notification",
            letter_config=LETTER_TYPES["institution_notification"],
            decedent_name="John Doe",
            date_of_death="January 15, 2025",
            estate_type="Testate Probate",
            jurisdiction="CA",
            executor_name="Jane Doe",
            executor_title="Executor/Trustee",
            institution="Chase Bank",
            account_number_masked="****1234",
            asset_title="Chase Checking Account",
            asset_type="Bank Account",
            asset_value="$50,000.00",
            court_case_number="2025-PR-001",
        )
        assert "John Doe" in prompt
        assert "January 15, 2025" in prompt
        assert "Chase Bank" in prompt
        assert "****1234" in prompt
        assert "Jane Doe" in prompt
        assert "2025-PR-001" in prompt

    def test_handles_missing_optional_fields(self):
        from app.services.ai_letter_service import LETTER_TYPES, _build_user_prompt

        prompt = _build_user_prompt(
            letter_type="creditor_notification",
            letter_config=LETTER_TYPES["creditor_notification"],
            decedent_name="Jane Smith",
            date_of_death=None,
            estate_type="Intestate Probate",
            jurisdiction="NY",
            executor_name=None,
            executor_title="Personal Representative",
            institution=None,
            account_number_masked=None,
            asset_title=None,
            asset_type=None,
            asset_value=None,
            court_case_number=None,
        )
        assert "Jane Smith" in prompt
        assert "NY" in prompt

    def test_includes_letter_purpose(self):
        from app.services.ai_letter_service import LETTER_TYPES, _build_user_prompt

        prompt = _build_user_prompt(
            letter_type="insurance_claim",
            letter_config=LETTER_TYPES["insurance_claim"],
            decedent_name="Test Person",
            date_of_death=None,
            estate_type="Testate Probate",
            jurisdiction="TX",
            executor_name=None,
            executor_title="Executor",
            institution="Prudential",
            account_number_masked=None,
            asset_title="Life Policy",
            asset_type="Life Insurance",
            asset_value="$500,000.00",
            court_case_number=None,
        )
        assert "death benefit" in prompt.lower() or "claim" in prompt.lower()


class TestBuildToolSchema:
    """Test tool-use schema for letter output."""

    def test_tool_name(self):
        from app.services.ai_letter_service import _build_tool_schema

        schema = _build_tool_schema()
        assert schema["name"] == "draft_letter"

    def test_has_required_fields(self):
        from app.services.ai_letter_service import _build_tool_schema

        schema = _build_tool_schema()
        props = schema["input_schema"]["properties"]
        assert "subject" in props
        assert "body" in props
        assert "recipient_institution" in props

    def test_all_fields_required(self):
        from app.services.ai_letter_service import _build_tool_schema

        schema = _build_tool_schema()
        required = schema["input_schema"]["required"]
        assert "subject" in required
        assert "body" in required
        assert "recipient_institution" in required


class TestEstimateCost:
    """Test cost estimation."""

    def test_zero_tokens_zero_cost(self):
        from app.services.ai_letter_service import _estimate_cost

        assert _estimate_cost(0, 0) == 0.0

    def test_known_values(self):
        from app.services.ai_letter_service import _estimate_cost

        cost = _estimate_cost(1_000_000, 1_000_000)
        assert cost == 18.0


class TestAILetterDraftResponse:
    """Test the response schema."""

    def test_valid_response(self):
        resp = AILetterDraftResponse(
            subject="Notice of Death — John Doe",
            body="Dear Sir/Madam,\n\nI am writing to inform you...",
            recipient_institution="Chase Bank",
        )
        assert resp.subject == "Notice of Death — John Doe"
        assert "Dear Sir/Madam" in resp.body
        assert resp.recipient_institution == "Chase Bank"


class TestDraftLetterService:
    """Test the main draft_letter service function."""

    @pytest.mark.asyncio
    async def test_invalid_letter_type_raises(self):
        from app.services.ai_letter_service import draft_letter

        mock_db = AsyncMock()
        with pytest.raises(ValueError, match="Unknown letter type"):
            await draft_letter(
                mock_db,
                matter_id=uuid4(),
                asset_id=uuid4(),
                letter_type="nonexistent_type",
            )

    @pytest.mark.asyncio
    async def test_missing_asset_raises(self):
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
    async def test_successful_draft(self):
        from app.services.ai_letter_service import draft_letter

        mock_db = AsyncMock()

        asset_id = uuid4()
        matter_id = uuid4()
        firm_id = uuid4()

        mock_asset = MagicMock()
        mock_asset.id = asset_id
        mock_asset.matter_id = matter_id
        mock_asset.title = "Chase Checking"
        mock_asset.institution = "Chase Bank"
        mock_asset.asset_type = MagicMock(value="bank_account")
        mock_asset.account_number_encrypted = None
        mock_asset.current_estimated_value = 50000
        mock_asset.date_of_death_value = None

        mock_matter = MagicMock()
        mock_matter.id = matter_id
        mock_matter.firm_id = firm_id
        mock_matter.decedent_name = "John Doe"
        mock_matter.date_of_death = MagicMock()
        mock_matter.date_of_death.strftime.return_value = "January 15, 2025"
        mock_matter.estate_type = MagicMock(value="testate_probate")
        mock_matter.jurisdiction_state = "CA"
        mock_matter.settings = {}

        mock_executor = MagicMock()
        mock_executor.full_name = "Jane Doe"

        mock_result_asset = MagicMock()
        mock_result_asset.scalar_one_or_none.return_value = mock_asset
        mock_result_matter = MagicMock()
        mock_result_matter.scalar_one_or_none.return_value = mock_matter
        mock_result_executor = MagicMock()
        mock_result_executor.scalars.return_value.first.return_value = mock_executor

        mock_db.execute.side_effect = [
            mock_result_asset,
            mock_result_matter,
            mock_result_executor,
        ]

        claude_result = {
            "subject": "Notice of Death — John Doe Estate",
            "body": "Dear Sir/Madam,\n\nI am writing to inform you of the death of John Doe...",
            "recipient_institution": "Chase Bank",
        }

        with (
            patch("app.services.ai_letter_service.check_rate_limit"),
            patch(
                "app.services.ai_letter_service._mask_account_number",
                return_value=None,
            ),
            patch(
                "app.services.ai_letter_service._call_claude",
                return_value=(claude_result, 800, 500),
            ),
            patch(
                "app.services.ai_letter_service.event_logger.log",
                new_callable=AsyncMock,
            ) as mock_event_log,
        ):
            result = await draft_letter(
                mock_db,
                matter_id=matter_id,
                asset_id=asset_id,
                letter_type="institution_notification",
            )

        assert result.subject == "Notice of Death — John Doe Estate"
        assert "John Doe" in result.body
        assert result.recipient_institution == "Chase Bank"

        # Verify event was logged
        mock_event_log.assert_called_once()
        call_kwargs = mock_event_log.call_args.kwargs
        assert call_kwargs["action"] == "letter_drafted"
        assert call_kwargs["actor_type"].value == "ai"

    def test_no_sensitive_info_in_system_prompt(self):
        """Ensure the system prompt warns against including sensitive info."""
        from app.services.ai_letter_service import _build_system_prompt

        prompt = _build_system_prompt()
        assert "never" in prompt.lower()

    def test_masked_account_in_prompt(self):
        """Account numbers in the prompt should be masked."""
        from app.services.ai_letter_service import LETTER_TYPES, _build_user_prompt

        prompt = _build_user_prompt(
            letter_type="institution_notification",
            letter_config=LETTER_TYPES["institution_notification"],
            decedent_name="Test",
            date_of_death=None,
            estate_type="Probate",
            jurisdiction="CA",
            executor_name=None,
            executor_title="Executor",
            institution="Bank",
            account_number_masked="****5678",
            asset_title="Account",
            asset_type="Bank Account",
            asset_value=None,
            court_case_number=None,
        )
        assert "****5678" in prompt


class TestDraftLetterCeleryTask:
    """Verify the Celery task is properly configured."""

    def test_task_exists(self):
        from app.workers.ai_tasks import draft_letter

        assert callable(draft_letter)

    def test_task_name(self):
        from app.workers.ai_tasks import draft_letter

        assert draft_letter.name == "app.workers.ai_tasks.draft_letter"


class TestAIRouteHasDraftLetter:
    """Verify the API route includes draft-letter endpoint."""

    def test_route_file_has_draft_letter(self):
        from pathlib import Path

        route_file = Path(__file__).parents[2] / "app" / "api" / "v1" / "ai" / "__init__.py"
        source = route_file.read_text()
        assert "draft-letter" in source
        assert "AILetterDraftRequest" in source
        assert "AILetterDraftResponse" in source

    def test_route_file_has_letter_types_endpoint(self):
        from pathlib import Path

        route_file = Path(__file__).parents[2] / "app" / "api" / "v1" / "ai" / "__init__.py"
        source = route_file.read_text()
        assert "letter-types" in source
