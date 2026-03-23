"""Unit tests for AI usage monitoring service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestGetUsageStats:
    """Test the get_usage_stats aggregation service."""

    @pytest.mark.asyncio
    async def test_returns_expected_fields(self):
        from app.services.ai_usage_service import get_usage_stats

        mock_db = AsyncMock()

        # Mock totals query
        mock_totals = MagicMock()
        mock_totals.total_calls = 25
        mock_totals.successful_calls = 23
        mock_totals.failed_calls = 2
        mock_totals.total_input_tokens = 50000
        mock_totals.total_output_tokens = 15000
        mock_totals.total_cost_usd = 0.225
        mock_totals_result = MagicMock()
        mock_totals_result.one.return_value = mock_totals

        # Mock by_operation query
        mock_op_row = MagicMock()
        mock_op_row.operation = "classify"
        mock_op_row.calls = 15
        mock_op_row.input_tokens = 30000
        mock_op_row.output_tokens = 5000
        mock_op_row.cost_usd = 0.165
        mock_by_op_result = MagicMock()
        mock_by_op_result.all.return_value = [mock_op_row]

        # Mock by_matter query
        matter_id = uuid4()
        mock_matter_row = MagicMock()
        mock_matter_row.matter_id = matter_id
        mock_matter_row.calls = 10
        mock_matter_row.cost_usd = 0.15
        mock_by_matter_result = MagicMock()
        mock_by_matter_result.all.return_value = [mock_matter_row]

        # Mock titles query
        mock_titles_result = MagicMock()
        mock_titles_result.all.return_value = [(matter_id, "Doe Estate")]

        mock_db.execute.side_effect = [
            mock_totals_result,
            mock_by_op_result,
            mock_by_matter_result,
            mock_titles_result,
        ]

        with patch("app.services.ai_usage_service.get_usage", return_value={"firm_calls_this_hour": 5}):
            result = await get_usage_stats(mock_db, firm_id=uuid4())

        assert result["total_calls"] == 25
        assert result["successful_calls"] == 23
        assert result["failed_calls"] == 2
        assert result["total_input_tokens"] == 50000
        assert result["total_output_tokens"] == 15000
        assert result["total_cost_usd"] == 0.225
        assert len(result["by_operation"]) == 1
        assert result["by_operation"][0]["operation"] == "classify"
        assert len(result["by_matter"]) == 1
        assert result["by_matter"][0]["matter_title"] == "Doe Estate"
        assert result["rate_limits"]["firm_calls_this_hour"] == 5
        assert result["rate_limits"]["firm_limit_per_hour"] == 100

    @pytest.mark.asyncio
    async def test_defaults_to_current_month(self):
        from app.services.ai_usage_service import get_usage_stats

        mock_db = AsyncMock()

        mock_totals = MagicMock()
        mock_totals.total_calls = 0
        mock_totals.successful_calls = 0
        mock_totals.failed_calls = 0
        mock_totals.total_input_tokens = 0
        mock_totals.total_output_tokens = 0
        mock_totals.total_cost_usd = 0.0
        mock_totals_result = MagicMock()
        mock_totals_result.one.return_value = mock_totals

        mock_empty = MagicMock()
        mock_empty.all.return_value = []

        mock_db.execute.side_effect = [
            mock_totals_result,
            mock_empty,  # by_operation
            mock_empty,  # by_matter
        ]

        with patch("app.services.ai_usage_service.get_usage", return_value={}):
            result = await get_usage_stats(mock_db, firm_id=uuid4())

        # period_start should be first of current month
        period = datetime.fromisoformat(result["period_start"])
        assert period.day == 1

    @pytest.mark.asyncio
    async def test_custom_since_date(self):
        from app.services.ai_usage_service import get_usage_stats

        mock_db = AsyncMock()

        mock_totals = MagicMock()
        mock_totals.total_calls = 0
        mock_totals.successful_calls = 0
        mock_totals.failed_calls = 0
        mock_totals.total_input_tokens = 0
        mock_totals.total_output_tokens = 0
        mock_totals.total_cost_usd = 0.0
        mock_totals_result = MagicMock()
        mock_totals_result.one.return_value = mock_totals

        mock_empty = MagicMock()
        mock_empty.all.return_value = []

        mock_db.execute.side_effect = [
            mock_totals_result,
            mock_empty,
            mock_empty,
        ]

        custom_since = datetime(2025, 6, 1, tzinfo=UTC)
        with patch("app.services.ai_usage_service.get_usage", return_value={}):
            result = await get_usage_stats(mock_db, firm_id=uuid4(), since=custom_since)

        assert result["period_start"] == custom_since.isoformat()

    @pytest.mark.asyncio
    async def test_empty_usage_returns_zeros(self):
        from app.services.ai_usage_service import get_usage_stats

        mock_db = AsyncMock()

        mock_totals = MagicMock()
        mock_totals.total_calls = 0
        mock_totals.successful_calls = 0
        mock_totals.failed_calls = 0
        mock_totals.total_input_tokens = 0
        mock_totals.total_output_tokens = 0
        mock_totals.total_cost_usd = 0.0
        mock_totals_result = MagicMock()
        mock_totals_result.one.return_value = mock_totals

        mock_empty = MagicMock()
        mock_empty.all.return_value = []

        mock_db.execute.side_effect = [
            mock_totals_result,
            mock_empty,
            mock_empty,
        ]

        with patch("app.services.ai_usage_service.get_usage", return_value={}):
            result = await get_usage_stats(mock_db, firm_id=uuid4())

        assert result["total_calls"] == 0
        assert result["total_cost_usd"] == 0.0
        assert result["by_operation"] == []
        assert result["by_matter"] == []


class TestUsageEndpointExists:
    def test_route_file_has_usage_stats(self):
        from pathlib import Path

        route_file = Path(__file__).parents[2] / "app" / "api" / "v1" / "ai" / "__init__.py"
        source = route_file.read_text()
        assert "usage-stats" in source
        assert "get_usage_stats" in source
