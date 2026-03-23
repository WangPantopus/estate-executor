"""Unit tests for AI usage log model."""

from __future__ import annotations


class TestAIUsageLogModel:
    """Verify AIUsageLog model structure."""

    def test_model_exists(self):
        from app.models.ai_usage_logs import AIUsageLog

        assert AIUsageLog is not None

    def test_table_name(self):
        from app.models.ai_usage_logs import AIUsageLog

        assert AIUsageLog.__tablename__ == "ai_usage_logs"

    def test_has_firm_id(self):
        from app.models.ai_usage_logs import AIUsageLog

        assert hasattr(AIUsageLog, "firm_id")

    def test_has_matter_id(self):
        from app.models.ai_usage_logs import AIUsageLog

        assert hasattr(AIUsageLog, "matter_id")

    def test_has_document_id(self):
        from app.models.ai_usage_logs import AIUsageLog

        assert hasattr(AIUsageLog, "document_id")

    def test_has_operation(self):
        from app.models.ai_usage_logs import AIUsageLog

        assert hasattr(AIUsageLog, "operation")

    def test_has_model(self):
        from app.models.ai_usage_logs import AIUsageLog

        assert hasattr(AIUsageLog, "model")

    def test_has_input_tokens(self):
        from app.models.ai_usage_logs import AIUsageLog

        assert hasattr(AIUsageLog, "input_tokens")

    def test_has_output_tokens(self):
        from app.models.ai_usage_logs import AIUsageLog

        assert hasattr(AIUsageLog, "output_tokens")

    def test_has_cost_estimate_usd(self):
        from app.models.ai_usage_logs import AIUsageLog

        assert hasattr(AIUsageLog, "cost_estimate_usd")

    def test_has_status(self):
        from app.models.ai_usage_logs import AIUsageLog

        assert hasattr(AIUsageLog, "status")

    def test_has_error_message(self):
        from app.models.ai_usage_logs import AIUsageLog

        assert hasattr(AIUsageLog, "error_message")

    def test_has_metadata(self):
        from app.models.ai_usage_logs import AIUsageLog

        assert hasattr(AIUsageLog, "metadata_")

    def test_has_created_at(self):
        from app.models.ai_usage_logs import AIUsageLog

        assert hasattr(AIUsageLog, "created_at")

    def test_no_updated_at(self):
        """AI usage logs are immutable — should not have updated_at."""
        from app.models.ai_usage_logs import AIUsageLog

        # The model inherits from Base (not BaseModel), so no auto updated_at
        col_names = {c.name for c in AIUsageLog.__table__.columns}
        assert "updated_at" not in col_names

    def test_registered_in_models_init(self):
        from app.models import AIUsageLog as ImportedModel

        assert ImportedModel is not None

    def test_indexes_exist(self):
        from app.models.ai_usage_logs import AIUsageLog

        index_names = {idx.name for idx in AIUsageLog.__table__.indexes}
        assert "ix_ai_usage_logs_firm_id_created_at" in index_names
        assert "ix_ai_usage_logs_matter_id" in index_names
        assert "ix_ai_usage_logs_operation" in index_names


class TestAIUsageLogMigration:
    """Verify the migration file exists and has correct structure."""

    def test_migration_file_exists(self):
        import importlib

        mod = importlib.import_module("migrations.versions.c3d4e5f6a7b8_add_ai_usage_logs")
        assert hasattr(mod, "upgrade")
        assert hasattr(mod, "downgrade")

    def test_migration_revision_chain(self):
        import importlib

        mod = importlib.import_module("migrations.versions.c3d4e5f6a7b8_add_ai_usage_logs")
        assert mod.revision == "c3d4e5f6a7b8"
        assert mod.down_revision == "b2c3d4e5f6a7"
