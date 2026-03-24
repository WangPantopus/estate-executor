"""Middleware for tenant isolation, request logging, and exception handling."""

from __future__ import annotations

import logging
import re
import traceback
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import (
    RequestTimer,
    firm_id_var,
    new_request_id,
    request_id_var,
    user_id_var,
)

if TYPE_CHECKING:
    from fastapi import Request, Response

logger = logging.getLogger(__name__)

# Pattern to extract firm_id from URL paths like /api/v1/firms/{firm_id}/...
_FIRM_ID_PATTERN = re.compile(r"/firms/([0-9a-f\-]{36})")


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Extract firm_id from URL path and store it in request state.

    The actual PostgreSQL SET LOCAL for RLS is executed in the get_db
    dependency (see dependencies.py) because the DB session isn't available
    at middleware level — it's created later via dependency injection.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        match = _FIRM_ID_PATTERN.search(request.url.path)
        if match:
            firm_id = match.group(1)
            request.state.firm_id = firm_id
        else:
            request.state.firm_id = None

        response: Response = await call_next(request)
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with timing, correlation ID, user_id, and firm_id.

    Sets contextvars so that ALL downstream log statements within this
    request automatically include request_id, user_id, and firm_id.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        # Generate and propagate correlation ID
        rid = new_request_id()
        request.state.request_id = rid
        request_id_var.set(rid)

        with RequestTimer() as timer:
            response: Response = await call_next(request)

        # Propagate user/firm context for downstream logging
        uid = getattr(request.state, "user_id", None)
        fid = getattr(request.state, "firm_id", None)
        if uid:
            user_id_var.set(str(uid))
        if fid:
            firm_id_var.set(str(fid))

        duration = round(timer.duration_ms, 2)

        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration,
            },
        )

        # Record metrics for performance monitoring
        from app.core.metrics import metrics_collector

        metrics_collector.record_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration,
        )

        response.headers["X-Request-ID"] = rid
        return response


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return RFC 7807 Problem Details JSON."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        try:
            return await call_next(request)  # type: ignore[no-any-return]
        except Exception as exc:
            rid = getattr(request.state, "request_id", new_request_id())

            logger.error(
                "unhandled_exception",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(exc),
                },
                exc_info=True,
            )

            # Report to Sentry if available
            try:
                import sentry_sdk

                sentry_sdk.capture_exception(exc)
            except ImportError:
                pass

            detail = str(exc) if not settings.is_production else "Internal server error"

            return JSONResponse(
                status_code=500,
                content={
                    "type": "about:blank",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": detail,
                    "instance": request.url.path,
                },
                headers={"X-Request-ID": rid},
            )
