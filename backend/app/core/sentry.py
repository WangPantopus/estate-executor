"""Sentry SDK initialization for error tracking and performance monitoring.

Call ``init_sentry()`` once during application startup (lifespan).
If SENTRY_DSN is empty, Sentry is silently disabled — no-op in development.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.core.config import settings

if TYPE_CHECKING:
    import sentry_sdk.types

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Initialize Sentry SDK if a DSN is configured."""
    if not settings.sentry_dsn:
        logger.info("sentry_disabled — SENTRY_DSN not set")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment or settings.app_env,
            release=f"estate-executor@{_get_version()}",
            traces_sample_rate=settings.sentry_traces_sample_rate,
            profiles_sample_rate=settings.sentry_profiles_sample_rate,
            # Attach user context from Auth0 JWT
            send_default_pii=False,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                StarletteIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                RedisIntegration(),
                CeleryIntegration(monitor_beat_tasks=True),
            ],
            # Filter out health check transactions to reduce noise
            traces_sampler=_traces_sampler,
            before_send=_before_send,
        )
        logger.info("sentry_initialized", extra={"component": "sentry"})
    except ImportError:
        logger.warning("sentry_sdk not installed — error tracking disabled")
    except Exception:
        logger.warning("sentry_init_failed", exc_info=True)


def _get_version() -> str:
    """Read version from pyproject.toml or fallback."""
    try:
        from importlib.metadata import version

        return version("estate-executor-api")
    except Exception:
        return "0.1.0"


def _traces_sampler(sampling_context: dict) -> float:  # type: ignore[type-arg]
    """Custom traces sampler — drop health checks, sample normally otherwise."""
    transaction_context = sampling_context.get("transaction_context", {})
    name = transaction_context.get("name", "")

    # Don't trace health checks
    if "/health" in name:
        return 0.0

    return settings.sentry_traces_sample_rate


def _before_send(
    event: sentry_sdk.types.Event, hint: dict[str, Any]
) -> sentry_sdk.types.Event | None:
    """Filter events before sending to Sentry.

    - Strip sensitive headers
    - Attach correlation ID
    """
    # Attach request_id if available
    from app.core.logging import request_id_var

    rid = request_id_var.get("")
    if rid:
        event.setdefault("tags", {})["request_id"] = rid

    # Remove sensitive headers
    request_data: dict[str, Any] = event.get("request", {})  # type: ignore[assignment]
    headers: dict[str, Any] = request_data.get("headers", {})
    for sensitive in ("authorization", "cookie", "x-api-key"):
        headers.pop(sensitive, None)

    return event
