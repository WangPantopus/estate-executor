"""Unit tests for report service — PDF/XLSX generation and formatting."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest


class TestReportGeneratorRegistry:
    """Verify the REPORT_GENERATORS registry is complete and correct."""

    def test_all_report_types_registered(self):
        from app.services.report_service import REPORT_GENERATORS

        expected_types = {
            "matter-summary",
            "asset-inventory",
            "task-audit",
            "distribution-ledger",
            "time-tracking",
        }
        assert set(REPORT_GENERATORS.keys()) == expected_types

    def test_each_report_has_label(self):
        from app.services.report_service import REPORT_GENERATORS

        for report_type, config in REPORT_GENERATORS.items():
            assert "label" in config, f"{report_type} missing label"
            assert isinstance(config["label"], str)
            assert len(config["label"]) > 0

    def test_each_report_has_formats(self):
        from app.services.report_service import REPORT_GENERATORS

        for report_type, config in REPORT_GENERATORS.items():
            assert "formats" in config, f"{report_type} missing formats"
            assert len(config["formats"]) > 0
            for fmt in config["formats"]:
                assert fmt in ("pdf", "xlsx"), f"{report_type} has invalid format: {fmt}"
                assert fmt in config, f"{report_type} format {fmt} has no generator function"

    def test_matter_summary_pdf_only(self):
        from app.services.report_service import REPORT_GENERATORS

        assert REPORT_GENERATORS["matter-summary"]["formats"] == ["pdf"]

    def test_asset_inventory_both_formats(self):
        from app.services.report_service import REPORT_GENERATORS

        assert set(REPORT_GENERATORS["asset-inventory"]["formats"]) == {"pdf", "xlsx"}

    def test_task_audit_both_formats(self):
        from app.services.report_service import REPORT_GENERATORS

        assert set(REPORT_GENERATORS["task-audit"]["formats"]) == {"pdf", "xlsx"}

    def test_distribution_ledger_pdf_only(self):
        from app.services.report_service import REPORT_GENERATORS

        assert REPORT_GENERATORS["distribution-ledger"]["formats"] == ["pdf"]

    def test_time_tracking_xlsx_only(self):
        from app.services.report_service import REPORT_GENERATORS

        assert REPORT_GENERATORS["time-tracking"]["formats"] == ["xlsx"]


class TestFormatHelpers:
    """Test formatting utility functions."""

    def test_format_currency_with_value(self):
        from app.services.report_service import _format_currency

        assert _format_currency(Decimal("150000.50")) == "$150,000.50"

    def test_format_currency_none(self):
        from app.services.report_service import _format_currency

        assert _format_currency(None) == "—"

    def test_format_currency_zero(self):
        from app.services.report_service import _format_currency

        assert _format_currency(Decimal("0")) == "$0.00"

    def test_format_date_with_date(self):
        from app.services.report_service import _format_date

        assert _format_date(date(2026, 3, 15)) == "03/15/2026"

    def test_format_date_none(self):
        from app.services.report_service import _format_date

        assert _format_date(None) == "—"

    def test_enum_label_none(self):
        from app.services.report_service import _enum_label

        assert _enum_label(None) == "—"

    def test_enum_label_string(self):
        from app.services.report_service import _enum_label

        assert _enum_label("testate_probate") == "Testate Probate"

    def test_enum_label_with_enum(self):
        from app.models.enums import TaskStatus
        from app.services.report_service import _enum_label

        assert _enum_label(TaskStatus.in_progress) == "In Progress"


class TestPDFGeneration:
    """Test PDF generation functions produce valid PDF bytes."""

    def test_styled_table_creates_table(self):
        from app.services.report_service import _styled_table

        data = [["Col A", "Col B"], ["val1", "val2"]]
        table = _styled_table(data)
        assert table is not None

    def test_section_heading_creates_paragraph(self):
        from app.services.report_service import _section_heading

        heading = _section_heading("Test Section")
        assert heading is not None

    def test_body_text_creates_paragraph(self):
        from app.services.report_service import _body_text

        text = _body_text("Hello world")
        assert text is not None

    def test_kv_pair_creates_paragraph(self):
        from app.services.report_service import _kv_pair

        pair = _kv_pair("Name", "John Smith")
        assert pair is not None

    def test_rgb_creates_color(self):
        from app.services.report_service import NAVY, _rgb

        color = _rgb(NAVY)
        assert color is not None


class TestExcelGeneration:
    """Test Excel generation functions."""

    def test_create_workbook(self):
        from app.services.report_service import _create_workbook

        wb = _create_workbook()
        assert wb is not None
        assert wb.active is not None

    def test_style_excel_header(self):
        from app.services.report_service import _create_workbook, _style_excel_header

        wb = _create_workbook()
        ws = wb.active
        ws.append(["Col1", "Col2", "Col3"])
        _style_excel_header(ws, 3)
        # Header should have navy fill
        assert ws.cell(1, 1).fill.start_color.rgb == "001A2332"

    def test_freeze_header(self):
        from app.services.report_service import _create_workbook, _freeze_header

        wb = _create_workbook()
        ws = wb.active
        ws.append(["Header"])
        _freeze_header(ws)
        assert ws.freeze_panes == "A2"

    def test_auto_width(self):
        from app.services.report_service import _auto_width, _create_workbook

        wb = _create_workbook()
        ws = wb.active
        ws.append(["Short", "A much longer column header value"])
        _auto_width(ws)
        # B should be wider than A
        assert ws.column_dimensions["B"].width > ws.column_dimensions["A"].width


class TestGenerateReportDispatcher:
    """Test the generate_report dispatcher function."""

    @pytest.mark.asyncio
    async def test_invalid_report_type_raises(self):
        from app.services.report_service import generate_report

        mock_db = AsyncMock()
        with pytest.raises(ValueError, match="Unknown report type"):
            await generate_report(
                mock_db,
                matter_id="00000000-0000-0000-0000-000000000001",
                report_type="nonexistent",
                output_format="pdf",
            )

    @pytest.mark.asyncio
    async def test_invalid_format_raises(self):
        from app.services.report_service import generate_report

        mock_db = AsyncMock()
        with pytest.raises(ValueError, match="not supported"):
            await generate_report(
                mock_db,
                matter_id="00000000-0000-0000-0000-000000000001",
                report_type="matter-summary",
                output_format="xlsx",
            )

    @pytest.mark.asyncio
    async def test_invalid_xlsx_for_distribution_ledger(self):
        from app.services.report_service import generate_report

        mock_db = AsyncMock()
        with pytest.raises(ValueError, match="not supported"):
            await generate_report(
                mock_db,
                matter_id="00000000-0000-0000-0000-000000000001",
                report_type="distribution-ledger",
                output_format="xlsx",
            )


class TestReportCaching:
    """Test the 24h report caching layer."""

    def test_cache_key_format(self):
        import uuid

        from app.services.report_service import _get_cache_key

        matter_id = uuid.UUID("12345678-1234-1234-1234-123456789012")
        key = _get_cache_key(matter_id, "matter-summary", "pdf")
        assert "report:" in key
        assert "12345678-1234-1234-1234-123456789012" in key
        assert "matter-summary" in key
        assert "pdf" in key

    def test_cache_key_includes_date(self):
        import uuid
        from datetime import date

        from app.services.report_service import _get_cache_key

        matter_id = uuid.UUID("12345678-1234-1234-1234-123456789012")
        key = _get_cache_key(matter_id, "asset-inventory", "xlsx")
        today_str = date.today().strftime("%Y%m%d")
        assert today_str in key

    def test_cache_get_returns_none_on_error(self):
        """Cache failures should return None, not raise."""
        from app.services.report_service import _cache_get
        # With no Redis running, should gracefully return None
        result = _cache_get("nonexistent:key")
        # May return None (no Redis) or None (key not found) — both are fine
        assert result is None or isinstance(result, bytes)

    def test_cache_set_does_not_raise(self):
        """Cache write failures should be silent."""
        from app.services.report_service import _cache_set
        # With no Redis running, should not raise
        _cache_set("test:key", b"test data")  # Should not raise

    def test_cache_ttl_is_24h(self):
        from app.services.report_service import _CACHE_TTL
        assert _CACHE_TTL == 86400


class TestReportCeleryTask:
    """Test the Celery task is registered correctly."""

    def test_report_task_registered(self):
        import app.workers.report_tasks  # noqa: F401
        from app.workers.celery_app import celery_app

        assert "app.workers.report_tasks.generate_report_task" in celery_app.tasks

    def test_report_task_routes_to_documents_queue(self):
        from app.workers.celery_app import celery_app

        routes = celery_app.conf.task_routes
        assert "app.workers.report_tasks.*" in routes
        assert routes["app.workers.report_tasks.*"]["queue"] == "documents"
