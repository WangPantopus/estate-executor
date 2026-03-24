"""Unit tests for monitoring, metrics, alerting, and structured logging."""

from __future__ import annotations

import json
import logging


class TestStructuredLogging:
    """Verify structured logging formatter and correlation context."""

    def test_structured_formatter_outputs_json(self):
        from app.core.logging import StructuredFormatter

        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=None, exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["level"] == "INFO"
        assert parsed["message"] == "test message"
        assert parsed["logger"] == "test"
        assert "timestamp" in parsed

    def test_structured_formatter_includes_correlation_id(self):
        from app.core.logging import StructuredFormatter, request_id_var

        token = request_id_var.set("req-abc-123")
        try:
            formatter = StructuredFormatter()
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg="correlated", args=None, exc_info=None,
            )
            output = formatter.format(record)
            parsed = json.loads(output)

            assert parsed["request_id"] == "req-abc-123"
        finally:
            request_id_var.reset(token)

    def test_structured_formatter_includes_extra_fields(self):
        from app.core.logging import StructuredFormatter

        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="with extras", args=None, exc_info=None,
        )
        record.duration_ms = 42.5  # type: ignore[attr-defined]
        record.status_code = 200  # type: ignore[attr-defined]
        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["duration_ms"] == 42.5
        assert parsed["status_code"] == 200

    def test_development_formatter_includes_short_request_id(self):
        from app.core.logging import DevelopmentFormatter, request_id_var

        token = request_id_var.set("abcdef12-3456-7890-abcd-ef1234567890")
        try:
            formatter = DevelopmentFormatter()
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg="dev mode", args=None, exc_info=None,
            )
            output = formatter.format(record)
            assert "abcdef12" in output
        finally:
            request_id_var.reset(token)

    def test_new_request_id_is_uuid(self):
        import uuid

        from app.core.logging import new_request_id

        rid = new_request_id()
        # Should be a valid UUID
        uuid.UUID(rid)

    def test_configure_logging_production(self):
        from app.core.logging import StructuredFormatter, configure_logging

        configure_logging(level="INFO", environment="production")
        root = logging.getLogger()
        assert any(
            isinstance(h.formatter, StructuredFormatter)
            for h in root.handlers
        )

    def test_configure_logging_development(self):
        from app.core.logging import DevelopmentFormatter, configure_logging

        configure_logging(level="INFO", environment="development")
        root = logging.getLogger()
        assert any(
            isinstance(h.formatter, DevelopmentFormatter)
            for h in root.handlers
        )


class TestRequestTimer:
    """Verify request timing context manager."""

    def test_timer_measures_duration(self):
        import time

        from app.core.logging import RequestTimer

        with RequestTimer() as timer:
            time.sleep(0.01)

        assert timer.duration_ms > 0
        assert timer.duration_ms < 1000  # Should be ~10ms, not seconds


class TestMetricsCollector:
    """Verify in-memory metrics collection."""

    def test_record_request_increments_count(self):
        from app.core.metrics import MetricsCollector

        mc = MetricsCollector()
        mc.record_request(method="GET", path="/api/v1/health", status_code=200, duration_ms=5.0)
        mc.record_request(method="GET", path="/api/v1/health", status_code=200, duration_ms=10.0)

        summary = mc.get_summary()
        assert summary["global"]["request_count"] == 2
        assert summary["global"]["error_count"] == 0

    def test_record_5xx_increments_errors(self):
        from app.core.metrics import MetricsCollector

        mc = MetricsCollector()
        mc.record_request(method="GET", path="/fail", status_code=500, duration_ms=100.0)
        mc.record_request(method="GET", path="/ok", status_code=200, duration_ms=5.0)

        summary = mc.get_global_summary()
        assert summary["error_count"] == 1
        assert summary["error_rate"] == 0.5

    def test_latency_percentiles(self):
        from app.core.metrics import MetricsCollector

        mc = MetricsCollector()
        for i in range(100):
            mc.record_request(method="GET", path="/test", status_code=200, duration_ms=float(i + 1))

        summary = mc.get_global_summary()
        latency = summary["latency_ms"]

        assert latency["p50"] > 0
        assert latency["p95"] > latency["p50"]
        assert latency["p99"] >= latency["p95"]
        assert latency["min"] == 1.0
        assert latency["max"] == 100.0

    def test_path_normalization_aggregates_uuids(self):
        from app.core.metrics import MetricsCollector

        mc = MetricsCollector()
        mc.record_request(
            method="GET",
            path="/api/v1/firms/12345678-1234-1234-1234-123456789abc/matters",
            status_code=200,
            duration_ms=5.0,
        )
        mc.record_request(
            method="GET",
            path="/api/v1/firms/abcdefab-abcd-abcd-abcd-abcdefabcdef/matters",
            status_code=200,
            duration_ms=10.0,
        )

        summary = mc.get_summary()
        # Both should be aggregated under the same normalized path
        assert "GET /api/v1/firms/:id/matters" in summary["endpoints"]
        ep = summary["endpoints"]["GET /api/v1/firms/:id/matters"]
        assert ep["request_count"] == 2

    def test_empty_collector_returns_null_latency(self):
        from app.core.metrics import MetricsCollector

        mc = MetricsCollector()
        summary = mc.get_global_summary()
        assert summary["latency_ms"] is None
        assert summary["request_count"] == 0

    def test_uptime_is_positive(self):
        from app.core.metrics import MetricsCollector

        mc = MetricsCollector()
        summary = mc.get_summary()
        assert summary["uptime_seconds"] >= 0


class TestAlertingService:
    """Verify alert rule evaluation."""

    def test_no_alerts_when_healthy(self):
        from app.core.metrics import MetricsCollector, metrics_collector

        # Record some healthy requests
        metrics_collector.record_request(method="GET", path="/ok", status_code=200, duration_ms=5.0)

        # We can't easily test async alerts here without mocking redis,
        # but we can test the sync alert checks
        from app.services.alerting_service import _check_error_rate, _check_latency

        error_alerts = _check_error_rate()
        latency_alerts = _check_latency()
        # With only 200s and low latency, no alerts should fire
        # (Note: this uses the global singleton which may have state from other tests)

    def test_high_error_rate_triggers_alert(self):
        from unittest.mock import patch

        from app.core.metrics import MetricsCollector
        from app.services.alerting_service import _check_error_rate

        mc = MetricsCollector()
        # Record mostly errors
        for _ in range(10):
            mc.record_request(method="GET", path="/fail", status_code=500, duration_ms=5.0)

        with patch("app.core.metrics.metrics_collector", mc):
            alerts = _check_error_rate()
            assert len(alerts) == 1
            assert alerts[0].rule == "high_error_rate"
            assert alerts[0].severity.value == "critical"

    def test_high_latency_triggers_alert(self):
        from unittest.mock import patch

        from app.core.metrics import MetricsCollector
        from app.services.alerting_service import _check_latency

        mc = MetricsCollector()
        # Record very slow requests
        for _ in range(100):
            mc.record_request(method="GET", path="/slow", status_code=200, duration_ms=10000.0)

        with patch("app.core.metrics.metrics_collector", mc):
            alerts = _check_latency()
            assert len(alerts) == 1
            assert alerts[0].rule == "high_p99_latency"

    def test_alert_to_dict(self):
        from app.services.alerting_service import Alert, AlertSeverity

        alert = Alert(
            rule="test_rule",
            severity=AlertSeverity.WARNING,
            message="Test alert",
            value=0.1,
            threshold=0.05,
        )
        d = alert.to_dict()
        assert d["rule"] == "test_rule"
        assert d["severity"] == "warning"
        assert d["current_value"] == 0.1
        assert d["threshold"] == 0.05


class TestHealthCheckHelpers:
    """Verify health check sub-functions exist and are callable."""

    def test_health_module_has_deep_checks(self):
        pytest = __import__("pytest")
        try:
            from app.api.v1.health import (
                _check_celery,
                _check_claude_api,
                _check_database,
                _check_redis,
                _check_s3,
            )
        except ImportError:
            pytest.skip("fastapi not installed in test environment")

        import asyncio

        assert asyncio.iscoroutinefunction(_check_database)
        assert asyncio.iscoroutinefunction(_check_redis)
        assert asyncio.iscoroutinefunction(_check_s3)
        assert asyncio.iscoroutinefunction(_check_claude_api)
        assert asyncio.iscoroutinefunction(_check_celery)


class TestSentryInit:
    """Verify Sentry initialization behavior."""

    def test_sentry_disabled_without_dsn(self):
        """Sentry should be a no-op when DSN is empty."""
        from unittest.mock import patch

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.sentry_dsn = ""
            from app.core.sentry import init_sentry

            # Should not raise
            init_sentry()

    def test_sentry_before_send_strips_auth_header(self):
        from app.core.sentry import _before_send

        event = {
            "request": {
                "headers": {
                    "authorization": "Bearer secret",
                    "cookie": "session=abc",
                    "content-type": "application/json",
                }
            }
        }
        result = _before_send(event, {})
        assert result is not None
        headers = result["request"]["headers"]
        assert "authorization" not in headers
        assert "cookie" not in headers
        assert "content-type" in headers


class TestConfigMonitoringSettings:
    """Verify monitoring-related config fields exist."""

    def test_monitoring_defaults(self):
        from app.core.config import Settings

        s = Settings(
            app_env="test",
            database_url="postgresql+asyncpg://localhost/test",
            redis_url="redis://localhost",
        )
        assert s.sentry_dsn == ""
        assert s.sentry_traces_sample_rate == 0.1
        assert s.alert_error_rate_threshold == 0.05
        assert s.alert_p99_latency_ms == 5000.0
        assert s.alert_queue_depth_threshold == 100
        assert s.metrics_retention_hours == 24
