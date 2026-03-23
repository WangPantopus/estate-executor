"""AI pipeline tests — confidence thresholds, chaining, and letter generation.

Tests the integration between pipeline stages: classification → extraction chaining,
confidence threshold filtering, and letter generation with various configurations.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.ai_classification_service import classify_document
from app.services.ai_extraction_service import EXTRACTABLE_TYPES
from app.services.ai_letter_service import LETTER_TYPES, draft_letter

# ─── Confidence Threshold Tests ───────────────────────────────────────────────


class TestConfidenceThresholdChaining:
    """Test auto-extraction chaining based on classification confidence."""

    def test_threshold_constant_is_0_7(self):
        from app.workers.ai_tasks import _AUTO_EXTRACT_CONFIDENCE_THRESHOLD

        assert _AUTO_EXTRACT_CONFIDENCE_THRESHOLD == 0.7

    @pytest.mark.asyncio
    async def test_high_confidence_extractable_type_triggers_extraction(self):
        """Classification with confidence >= 0.7 and extractable type should chain."""
        from app.workers.ai_tasks import classify_document as classify_task

        mock_classify_result = {
            "document_id": "doc-123",
            "status": "classified",
            "doc_type": "account_statement",
            "confidence": 0.85,
        }

        with (
            patch(
                "app.workers.ai_tasks._run_async",
                return_value=mock_classify_result,
            ),
            patch(
                "app.workers.ai_tasks.extract_document_data"
            ) as mock_extract_task,
        ):
            result = classify_task("doc-123", "matter-123")

        assert result["doc_type"] == "account_statement"
        # extract_document_data.delay should have been called
        mock_extract_task.delay.assert_called_once_with("doc-123", "matter-123")

    @pytest.mark.asyncio
    async def test_low_confidence_does_not_trigger_extraction(self):
        """Classification with confidence < 0.7 should NOT chain extraction."""
        from app.workers.ai_tasks import classify_document as classify_task

        mock_classify_result = {
            "document_id": "doc-123",
            "status": "classified",
            "doc_type": "account_statement",
            "confidence": 0.55,
        }

        with (
            patch(
                "app.workers.ai_tasks._run_async",
                return_value=mock_classify_result,
            ),
            patch(
                "app.workers.ai_tasks.extract_document_data"
            ) as mock_extract_task,
        ):
            result = classify_task("doc-123", "matter-123")

        mock_extract_task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_extractable_type_does_not_trigger_extraction(self):
        """Death certificate (not extractable) should NOT chain extraction."""
        from app.workers.ai_tasks import classify_document as classify_task

        mock_classify_result = {
            "document_id": "doc-123",
            "status": "classified",
            "doc_type": "death_certificate",
            "confidence": 0.95,
        }

        with (
            patch(
                "app.workers.ai_tasks._run_async",
                return_value=mock_classify_result,
            ),
            patch(
                "app.workers.ai_tasks.extract_document_data"
            ) as mock_extract_task,
        ):
            result = classify_task("doc-123", "matter-123")

        mock_extract_task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_confidence_exactly_at_threshold_triggers(self):
        """Confidence exactly == 0.7 should trigger extraction."""
        from app.workers.ai_tasks import classify_document as classify_task

        mock_classify_result = {
            "document_id": "doc-123",
            "status": "classified",
            "doc_type": "deed",
            "confidence": 0.7,
        }

        with (
            patch(
                "app.workers.ai_tasks._run_async",
                return_value=mock_classify_result,
            ),
            patch(
                "app.workers.ai_tasks.extract_document_data"
            ) as mock_extract_task,
        ):
            classify_task("doc-123", "matter-123")

        mock_extract_task.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_confidence_just_below_threshold_does_not_trigger(self):
        """Confidence 0.69 should NOT trigger extraction."""
        from app.workers.ai_tasks import classify_document as classify_task

        mock_classify_result = {
            "document_id": "doc-123",
            "status": "classified",
            "doc_type": "deed",
            "confidence": 0.69,
        }

        with (
            patch(
                "app.workers.ai_tasks._run_async",
                return_value=mock_classify_result,
            ),
            patch(
                "app.workers.ai_tasks.extract_document_data"
            ) as mock_extract_task,
        ):
            classify_task("doc-123", "matter-123")

        mock_extract_task.delay.assert_not_called()


class TestExtractableTypesCompleteness:
    """Verify all extractable types are properly handled."""

    def test_extractable_types_count(self):
        assert len(EXTRACTABLE_TYPES) == 6

    def test_extractable_types_are_subset_of_doc_types(self):
        from app.services.ai_classification_service import DOCUMENT_TYPES

        for t in EXTRACTABLE_TYPES:
            assert t in DOCUMENT_TYPES, f"{t} is extractable but not a valid doc type"

    @pytest.mark.parametrize("doc_type", sorted(EXTRACTABLE_TYPES))
    def test_each_extractable_type_triggers_chaining(self, doc_type):
        """Every extractable type with high confidence should trigger extraction."""
        from app.workers.ai_tasks import classify_document as classify_task

        mock_result = {
            "document_id": "doc-123",
            "status": "classified",
            "doc_type": doc_type,
            "confidence": 0.85,
        }

        with (
            patch("app.workers.ai_tasks._run_async", return_value=mock_result),
            patch("app.workers.ai_tasks.extract_document_data") as mock_extract,
        ):
            classify_task("doc-123", "matter-123")

        mock_extract.delay.assert_called_once()


# ─── Letter Generation Tests ─────────────────────────────────────────────────


def _make_letter_mocks(
    *,
    institution: str = "Chase Bank",
    asset_type: str = "bank_account",
    value: float = 50000,
    has_executor: bool = True,
    has_date_of_death: bool = True,
):
    """Create mocks for letter drafting with configurable parameters."""
    mock_db = AsyncMock()
    asset_id = uuid4()
    matter_id = uuid4()
    firm_id = uuid4()

    mock_asset = MagicMock()
    mock_asset.id = asset_id
    mock_asset.matter_id = matter_id
    mock_asset.title = f"{institution} Account"
    mock_asset.institution = institution
    mock_asset.asset_type = MagicMock(value=asset_type)
    mock_asset.account_number_encrypted = None
    mock_asset.current_estimated_value = value
    mock_asset.date_of_death_value = None

    mock_matter = MagicMock()
    mock_matter.id = matter_id
    mock_matter.firm_id = firm_id
    mock_matter.decedent_name = "John Doe"
    if has_date_of_death:
        mock_matter.date_of_death = MagicMock()
        mock_matter.date_of_death.strftime.return_value = "January 15, 2025"
    else:
        mock_matter.date_of_death = None
    mock_matter.estate_type = MagicMock(value="testate_probate")
    mock_matter.jurisdiction_state = "CA"
    mock_matter.settings = {}

    mock_executor = MagicMock()
    mock_executor.full_name = "Jane Doe" if has_executor else None

    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = mock_asset
    r2 = MagicMock()
    r2.scalar_one_or_none.return_value = mock_matter
    r3 = MagicMock()
    if has_executor:
        r3.scalars.return_value.first.return_value = mock_executor
    else:
        r3.scalars.return_value.first.return_value = None
    mock_db.execute.side_effect = [r1, r2, r3]

    return mock_db, matter_id, asset_id


class TestLetterGenerationVariations:
    """Test letter generation with various matter configurations."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("letter_type", sorted(LETTER_TYPES.keys()))
    async def test_all_letter_types_generate_successfully(self, letter_type):
        """Every letter type should generate without errors."""
        mock_db, matter_id, asset_id = _make_letter_mocks()

        claude_result = {
            "subject": f"Test {letter_type} letter",
            "body": f"Dear Sir/Madam,\n\nThis is a {letter_type} letter.\n\nSincerely,\nJane Doe",
            "recipient_institution": "Chase Bank",
        }

        with (
            patch("app.services.ai_letter_service.check_rate_limit"),
            patch("app.services.ai_letter_service._mask_account_number", return_value=None),
            patch(
                "app.services.ai_letter_service._call_claude",
                return_value=(claude_result, 500, 300),
            ),
            patch(
                "app.services.ai_letter_service.event_logger.log",
                new_callable=AsyncMock,
            ),
        ):
            result = await draft_letter(
                mock_db,
                matter_id=matter_id,
                asset_id=asset_id,
                letter_type=letter_type,
            )

        assert len(result.subject) > 0
        assert len(result.body) > 0
        assert len(result.recipient_institution) > 0

    @pytest.mark.asyncio
    async def test_letter_without_executor(self):
        """Letter should still generate when no executor/trustee is found."""
        mock_db, matter_id, asset_id = _make_letter_mocks(has_executor=False)

        # Need a 4th mock for the admin fallback query
        r4 = MagicMock()
        r4.scalars.return_value.first.return_value = None
        mock_db.execute.side_effect = list(mock_db.execute.side_effect) + [r4]

        claude_result = {
            "subject": "Notice of Death",
            "body": "Dear Sir/Madam,\n\nI am writing...",
            "recipient_institution": "Chase Bank",
        }

        with (
            patch("app.services.ai_letter_service.check_rate_limit"),
            patch("app.services.ai_letter_service._mask_account_number", return_value=None),
            patch(
                "app.services.ai_letter_service._call_claude",
                return_value=(claude_result, 400, 250),
            ),
            patch(
                "app.services.ai_letter_service.event_logger.log",
                new_callable=AsyncMock,
            ),
        ):
            result = await draft_letter(
                mock_db,
                matter_id=matter_id,
                asset_id=asset_id,
                letter_type="institution_notification",
            )

        assert len(result.body) > 0

    @pytest.mark.asyncio
    async def test_letter_without_date_of_death(self):
        """Letter should generate even without a date of death."""
        mock_db, matter_id, asset_id = _make_letter_mocks(has_date_of_death=False)

        claude_result = {
            "subject": "Notice of Death",
            "body": "Dear Sir/Madam,\n\nI am writing...",
            "recipient_institution": "Chase Bank",
        }

        with (
            patch("app.services.ai_letter_service.check_rate_limit"),
            patch("app.services.ai_letter_service._mask_account_number", return_value=None),
            patch(
                "app.services.ai_letter_service._call_claude",
                return_value=(claude_result, 400, 250),
            ),
            patch(
                "app.services.ai_letter_service.event_logger.log",
                new_callable=AsyncMock,
            ),
        ):
            result = await draft_letter(
                mock_db,
                matter_id=matter_id,
                asset_id=asset_id,
                letter_type="institution_notification",
            )

        assert len(result.body) > 0

    @pytest.mark.asyncio
    async def test_letter_for_insurance_asset(self):
        """Insurance claim letter should work with life_insurance asset type."""
        mock_db, matter_id, asset_id = _make_letter_mocks(
            institution="Prudential",
            asset_type="life_insurance",
            value=500000,
        )

        claude_result = {
            "subject": "Life Insurance Claim — Policy PLI-123",
            "body": "Dear Claims Department,\n\nI am filing...",
            "recipient_institution": "Prudential",
        }

        with (
            patch("app.services.ai_letter_service.check_rate_limit"),
            patch("app.services.ai_letter_service._mask_account_number", return_value="****1234"),
            patch(
                "app.services.ai_letter_service._call_claude",
                return_value=(claude_result, 600, 400),
            ),
            patch(
                "app.services.ai_letter_service.event_logger.log",
                new_callable=AsyncMock,
            ),
        ):
            result = await draft_letter(
                mock_db,
                matter_id=matter_id,
                asset_id=asset_id,
                letter_type="insurance_claim",
            )

        assert "Prudential" in result.recipient_institution


# ─── Cost Estimation Tests ────────────────────────────────────────────────────


class TestCostEstimation:
    """Test cost estimation across all services."""

    def test_classification_cost(self):
        from app.services.ai_classification_service import _estimate_cost

        cost = _estimate_cost(1000, 200)
        assert cost > 0
        assert isinstance(cost, float)

    def test_extraction_cost(self):
        from app.services.ai_extraction_service import _estimate_cost

        cost = _estimate_cost(2000, 500)
        assert cost > 0

    def test_letter_cost(self):
        from app.services.ai_letter_service import _estimate_cost

        cost = _estimate_cost(800, 1500)
        assert cost > 0

    def test_suggestion_cost(self):
        from app.services.ai_suggestion_service import _estimate_cost

        cost = _estimate_cost(3000, 1000)
        assert cost > 0

    def test_anomaly_cost(self):
        from app.services.ai_anomaly_service import _estimate_cost

        cost = _estimate_cost(2500, 800)
        assert cost > 0

    def test_all_services_use_same_pricing(self):
        """All services should use the same per-token pricing."""
        from app.services.ai_classification_service import _estimate_cost as c1
        from app.services.ai_extraction_service import _estimate_cost as c2
        from app.services.ai_letter_service import _estimate_cost as c3

        tokens = (1_000_000, 1_000_000)
        assert c1(*tokens) == c2(*tokens) == c3(*tokens) == 18.0
