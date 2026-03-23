"""Unit tests for AI feedback service and model."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest


class TestAIFeedbackModel:
    """Verify AIFeedback model structure."""

    def test_model_exists(self):
        from app.models.ai_feedback import AIFeedback

        assert AIFeedback is not None

    def test_table_name(self):
        from app.models.ai_feedback import AIFeedback

        assert AIFeedback.__tablename__ == "ai_feedback"

    def test_has_required_columns(self):
        from app.models.ai_feedback import AIFeedback

        for col in [
            "firm_id",
            "matter_id",
            "entity_type",
            "entity_id",
            "feedback_type",
            "ai_output",
            "user_correction",
            "corrected_by",
            "model_used",
            "metadata_",
            "created_at",
        ]:
            assert hasattr(AIFeedback, col), f"Missing column: {col}"

    def test_no_updated_at(self):
        """Feedback records are immutable."""
        from app.models.ai_feedback import AIFeedback

        col_names = {c.name for c in AIFeedback.__table__.columns}
        assert "updated_at" not in col_names

    def test_registered_in_models_init(self):
        from app.models import AIFeedback

        assert AIFeedback is not None

    def test_indexes_exist(self):
        from app.models.ai_feedback import AIFeedback

        index_names = {idx.name for idx in AIFeedback.__table__.indexes}
        assert "ix_ai_feedback_firm_id_created_at" in index_names
        assert "ix_ai_feedback_feedback_type" in index_names
        assert "ix_ai_feedback_entity_id" in index_names


class TestAIFeedbackMigration:
    def test_migration_exists(self):
        import importlib

        mod = importlib.import_module("migrations.versions.d4e5f6a7b8c9_add_ai_feedback")
        assert mod.revision == "d4e5f6a7b8c9"
        assert mod.down_revision == "c3d4e5f6a7b8"


class TestLogClassificationCorrection:
    @pytest.mark.asyncio
    async def test_correction_logged(self):
        from app.services.ai_feedback_service import log_classification_correction

        mock_db = AsyncMock()
        doc_id = uuid4()

        result = await log_classification_correction(
            mock_db,
            firm_id=uuid4(),
            matter_id=uuid4(),
            document_id=doc_id,
            original_doc_type="account_statement",
            original_confidence=0.85,
            corrected_doc_type="insurance_policy",
            corrected_by=uuid4(),
        )

        assert result.feedback_type == "classification_correction"
        assert result.ai_output["doc_type"] == "account_statement"
        assert result.user_correction["doc_type"] == "insurance_policy"
        assert result.metadata_["was_correction"] is True
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirmation_logged_differently(self):
        from app.services.ai_feedback_service import log_classification_correction

        mock_db = AsyncMock()

        result = await log_classification_correction(
            mock_db,
            firm_id=uuid4(),
            matter_id=uuid4(),
            document_id=uuid4(),
            original_doc_type="death_certificate",
            original_confidence=0.95,
            corrected_doc_type="death_certificate",  # Same type = confirmation
        )

        assert result.feedback_type == "classification_confirmation"
        assert result.metadata_["was_correction"] is False

    @pytest.mark.asyncio
    async def test_none_original_is_confirmation(self):
        """When there was no AI classification, user setting a type is a confirmation."""
        from app.services.ai_feedback_service import log_classification_correction

        mock_db = AsyncMock()

        result = await log_classification_correction(
            mock_db,
            firm_id=uuid4(),
            matter_id=uuid4(),
            document_id=uuid4(),
            original_doc_type=None,
            original_confidence=None,
            corrected_doc_type="will",
        )

        assert result.feedback_type == "classification_confirmation"
        assert result.metadata_["was_correction"] is False


class TestLogExtractionCorrection:
    @pytest.mark.asyncio
    async def test_extraction_correction_logged(self):
        from app.services.ai_feedback_service import log_extraction_correction

        mock_db = AsyncMock()

        result = await log_extraction_correction(
            mock_db,
            firm_id=uuid4(),
            matter_id=uuid4(),
            document_id=uuid4(),
            original_extracted_data={
                "institution": "Chase",
                "balance": 50000,
                "_extraction_metadata": {"model": "test"},
            },
            corrected_fields={
                "institution": "Chase Bank",
                "balance": 52000,
            },
        )

        assert result.feedback_type == "extraction_correction"
        assert result.ai_output["institution"] == "Chase"
        assert "_extraction_metadata" not in result.ai_output  # Internal fields excluded
        assert result.user_correction["institution"] == "Chase Bank"
        assert result.metadata_["change_count"] == 2
        assert "institution" in result.metadata_["changed_fields"]
        assert "balance" in result.metadata_["changed_fields"]

    @pytest.mark.asyncio
    async def test_no_changes_still_logged(self):
        from app.services.ai_feedback_service import log_extraction_correction

        mock_db = AsyncMock()

        result = await log_extraction_correction(
            mock_db,
            firm_id=uuid4(),
            matter_id=uuid4(),
            document_id=uuid4(),
            original_extracted_data={"institution": "Chase"},
            corrected_fields={"institution": "Chase"},  # Same value
        )

        assert result.metadata_["change_count"] == 0

    @pytest.mark.asyncio
    async def test_none_original_data(self):
        from app.services.ai_feedback_service import log_extraction_correction

        mock_db = AsyncMock()

        result = await log_extraction_correction(
            mock_db,
            firm_id=uuid4(),
            matter_id=uuid4(),
            document_id=uuid4(),
            original_extracted_data=None,
            corrected_fields={"institution": "New Bank"},
        )

        assert result.metadata_["change_count"] == 1


class TestFeedbackIntegrationWithDocService:
    """Test that confirm_doc_type calls feedback logging."""

    def test_confirm_doc_type_calls_feedback(self):
        """Verify the document service has feedback integration."""
        import inspect

        from app.services.document_service import confirm_doc_type

        source = inspect.getsource(confirm_doc_type)
        assert "log_classification_correction" in source
        assert "ai_feedback_service" in source
