"""Alerting service — evaluates alert rules and returns active alerts.

Alert rules from the design doc:
1. Error rate exceeds threshold (5% default)
2. P99 latency exceeds threshold (5s default)
3. Celery queue depth exceeds threshold
4. Deadline task failures in the last N hours
5. Database connection pool saturation
6. Redis connection failures

Alerts are evaluated on-demand (pull model) via the /api/v1/alerts endpoint.
For push-based alerting, integrate with PagerDuty/Opsgenie/Slack via webhooks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Alert:
    rule: str
    severity: AlertSeverity
    message: str
    value: Any
    threshold: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "severity": self.severity.value,
            "message": self.message,
            "current_value": self.value,
            "threshold": self.threshold,
        }


async def evaluate_alerts() -> list[Alert]:
    """Evaluate all alert rules and return any that are currently firing."""
    alerts: list[Alert] = []

    alerts.extend(_check_error_rate())
    alerts.extend(_check_latency())
    alerts.extend(await _check_queue_depth())
    alerts.extend(await _check_db_pool())
    alerts.extend(await _check_deadline_failures())
    alerts.extend(await _check_redis_connectivity())
    alerts.extend(await _check_uptime_monitors())

    return alerts


def _check_error_rate() -> list[Alert]:
    """Check if the global error rate exceeds the threshold."""
    from app.core.metrics import metrics_collector

    summary = metrics_collector.get_global_summary()
    error_rate = summary.get("error_rate", 0.0)
    threshold = settings.alert_error_rate_threshold

    alerts: list[Alert] = []
    if error_rate > threshold:
        alerts.append(
            Alert(
                rule="high_error_rate",
                severity=AlertSeverity.CRITICAL,
                message=f"Error rate {error_rate:.2%} exceeds threshold {threshold:.2%}",
                value=error_rate,
                threshold=threshold,
            )
        )
    return alerts


def _check_latency() -> list[Alert]:
    """Check if P99 latency exceeds the threshold."""
    from app.core.metrics import metrics_collector

    summary = metrics_collector.get_global_summary()
    latency = summary.get("latency_ms")
    if not latency:
        return []

    p99 = latency.get("p99", 0.0)
    threshold = settings.alert_p99_latency_ms

    alerts: list[Alert] = []
    if p99 > threshold:
        alerts.append(
            Alert(
                rule="high_p99_latency",
                severity=AlertSeverity.WARNING,
                message=f"P99 latency {p99:.0f}ms exceeds threshold {threshold:.0f}ms",
                value=p99,
                threshold=threshold,
            )
        )
    return alerts


async def _check_queue_depth() -> list[Alert]:
    """Check Celery queue depths in Redis."""
    alerts: list[Alert] = []
    threshold = settings.alert_queue_depth_threshold

    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.celery_broker_url, decode_responses=True)
        try:
            queues = ["default", "ai", "notifications", "documents"]
            for queue_name in queues:
                depth = await r.llen(queue_name)
                if depth > threshold:
                    alerts.append(
                        Alert(
                            rule="high_queue_depth",
                            severity=AlertSeverity.WARNING,
                            message=f"Queue '{queue_name}' depth {depth} exceeds threshold {threshold}",
                            value=depth,
                            threshold=threshold,
                        )
                    )
        finally:
            await r.aclose()
    except Exception as exc:
        logger.warning("alert_check_failed", extra={"check": "queue_depth", "error": str(exc)})
        alerts.append(
            Alert(
                rule="queue_check_failed",
                severity=AlertSeverity.CRITICAL,
                message=f"Unable to check queue depth: {exc}",
                value=None,
                threshold=threshold,
            )
        )

    return alerts


async def _check_db_pool() -> list[Alert]:
    """Check database connection pool saturation."""
    alerts: list[Alert] = []

    try:
        from app.core.database import engine

        pool = engine.pool
        pool_size = pool.size()
        checked_out = pool.checkedout()

        # Alert if >80% of pool is in use
        total_available = pool_size + engine.pool._max_overflow  # type: ignore[attr-defined]
        utilization = checked_out / total_available if total_available > 0 else 0.0

        if utilization > 0.8:
            alerts.append(
                Alert(
                    rule="db_pool_saturation",
                    severity=AlertSeverity.WARNING,
                    message=(
                        f"DB pool {utilization:.0%} utilized "
                        f"({checked_out}/{total_available} connections)"
                    ),
                    value=utilization,
                    threshold=0.8,
                )
            )
    except Exception as exc:
        logger.warning("alert_check_failed", extra={"check": "db_pool", "error": str(exc)})

    return alerts


async def _check_deadline_failures() -> list[Alert]:
    """Check for deadlines missed within the configured alert window.

    Queries for deadlines whose due_date fell within the last
    alert_deadline_failure_window_hours hours and whose status is 'missed'
    (i.e., the deadline passed without being completed or extended).
    """
    alerts: list[Alert] = []
    window_hours = settings.alert_deadline_failure_window_hours

    try:
        from datetime import UTC, date, datetime, timedelta

        from sqlalchemy import func, select

        from app.core.database import async_session_factory
        from app.models.deadlines import Deadline
        from app.models.enums import DeadlineStatus

        today = date.today()
        window_start = (datetime.now(UTC) - timedelta(hours=window_hours)).date()

        async with async_session_factory() as session:
            result = await session.execute(
                select(func.count(Deadline.id)).where(
                    Deadline.due_date >= window_start,
                    Deadline.due_date < today,
                    Deadline.status == DeadlineStatus.missed,
                )
            )
            missed_count = result.scalar() or 0

        if missed_count > 0:
            alerts.append(
                Alert(
                    rule="deadline_failures",
                    severity=AlertSeverity.CRITICAL,
                    message=(
                        f"{missed_count} deadline(s) missed in the last {window_hours}h "
                        f"without completion or extension"
                    ),
                    value=missed_count,
                    threshold=0,
                )
            )
    except Exception as exc:
        logger.warning("alert_check_failed", extra={"check": "deadline_failures", "error": str(exc)})

    return alerts


async def _check_uptime_monitors() -> list[Alert]:
    """Pull monitor statuses from UptimeRobot and alert on any that are down.

    Requires UPTIMEROBOT_READONLY_API_KEY to be set. Silently skips if the
    key is absent (e.g., in development).

    UptimeRobot status codes:
      0 = paused, 1 = not checked yet, 2 = up, 8 = seems down, 9 = down
    """
    alerts: list[Alert] = []
    api_key = settings.uptimerobot_readonly_api_key
    if not api_key:
        return alerts

    # Status codes that indicate a problem
    _DOWN_STATUSES = {8: "seems down", 9: "down"}

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.uptimerobot.com/v2/getMonitors",
                data={"api_key": api_key, "format": "json", "logs": "0"},
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("stat") != "ok":
            logger.warning(
                "alert_check_failed",
                extra={"check": "uptime_monitors", "error": data.get("error", {})},
            )
            return alerts

        for monitor in data.get("monitors", []):
            status_code = monitor.get("status")
            if status_code in _DOWN_STATUSES:
                name = monitor.get("friendly_name", monitor.get("url", "unknown"))
                label = _DOWN_STATUSES[status_code]
                alerts.append(
                    Alert(
                        rule="uptime_monitor_down",
                        severity=AlertSeverity.CRITICAL,
                        message=f"UptimeRobot monitor '{name}' is {label}",
                        value=label,
                        threshold="up",
                    )
                )
    except Exception as exc:
        logger.warning("alert_check_failed", extra={"check": "uptime_monitors", "error": str(exc)})

    return alerts


async def _check_redis_connectivity() -> list[Alert]:
    """Check Redis availability with a PING.

    Distinct from the queue depth check — this isolates a Redis connectivity
    failure from a merely deep queue, so each alert has a clear root cause.
    """
    alerts: list[Alert] = []

    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, decode_responses=True, socket_timeout=2)
        try:
            pong = await r.ping()
            if not pong:
                alerts.append(
                    Alert(
                        rule="redis_connection_failure",
                        severity=AlertSeverity.CRITICAL,
                        message="Redis PING returned False — cache and queue unavailable",
                        value=False,
                        threshold=True,
                    )
                )
        finally:
            await r.aclose()
    except Exception as exc:
        logger.warning("alert_check_failed", extra={"check": "redis", "error": str(exc)})
        alerts.append(
            Alert(
                rule="redis_connection_failure",
                severity=AlertSeverity.CRITICAL,
                message=f"Redis connection failed: {exc}",
                value=str(exc),
                threshold=None,
            )
        )

    return alerts
