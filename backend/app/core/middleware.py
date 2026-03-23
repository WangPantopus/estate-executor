"""Middleware for tenant isolation, request logging, and exception handling."""

from __future__ import annotations

import json
import logging
import re
import time
import traceback
import uuid
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

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
    """Log every request with timing, request ID, user_id, and firm_id."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.perf_counter()

        response: Response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        user_id = getattr(request.state, "user_id", None)
        firm_id = getattr(request.state, "firm_id", None)

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "user_id": str(user_id) if user_id else None,
            "firm_id": str(firm_id) if firm_id else None,
        }

        logger.info(json.dumps(log_data))

        response.headers["X-Request-ID"] = request_id
        return response


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return RFC 7807 Problem Details JSON."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

            logger.error(
                json.dumps(
                    {
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                    }
                )
            )

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
                headers={"X-Request-ID": request_id},
            )
