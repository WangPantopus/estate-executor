"""Structured logging with correlation IDs.

Provides JSON-formatted log output with automatic context propagation
(request_id, user_id, firm_id) across all log statements within a request.
Uses contextvars for thread/async-safe correlation ID propagation.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import time
from typing import Any
from uuid import uuid4

# ── Context variables for correlation ──────────────────────────────────────
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id", default="")
firm_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("firm_id", default="")


def new_request_id() -> str:
    """Generate a new correlation ID for a request."""
    return str(uuid4())


class StructuredFormatter(logging.Formatter):
    """JSON log formatter that includes correlation context automatically."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject correlation context from contextvars
        req_id = request_id_var.get("")
        if req_id:
            log_entry["request_id"] = req_id
        uid = user_id_var.get("")
        if uid:
            log_entry["user_id"] = uid
        fid = firm_id_var.get("")
        if fid:
            log_entry["firm_id"] = fid

        # Include extra fields passed via logger.info("msg", extra={...})
        for key in (
            "event_id",
            "matter_id",
            "entity_type",
            "entity_id",
            "action",
            "duration_ms",
            "status_code",
            "method",
            "path",
            "error",
            "component",
            "check",
            "metric",
        ):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        # Include exception info if present
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable formatter for development that still includes correlation IDs."""

    COLORS = {
        "DEBUG": "\033[36m",  # cyan
        "INFO": "\033[32m",  # green
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",  # red
        "CRITICAL": "\033[41m",  # red bg
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        req_id = request_id_var.get("")
        prefix = f"[{req_id[:8]}] " if req_id else ""
        msg = record.getMessage()

        base = f"{color}{record.levelname:8s}{self.RESET} {prefix}{record.name} — {msg}"

        if record.exc_info and record.exc_info[1] is not None:
            base += "\n" + self.formatException(record.exc_info)

        return base


def configure_logging(*, level: str = "INFO", environment: str = "development") -> None:
    """Configure root logger with structured or development formatting.

    Call once at application startup before any log statements.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicate output
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if environment in ("production", "staging"):
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(DevelopmentFormatter())

    root.addHandler(handler)

    # Reduce noise from third-party libraries
    for noisy in (
        "uvicorn.access",
        "uvicorn.error",
        "httpcore",
        "httpx",
        "urllib3",
        "botocore",
        "boto3",
        "celery",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)


class RequestTimer:
    """Context manager for timing request duration."""

    __slots__ = ("_start", "duration_ms")

    def __init__(self) -> None:
        self._start = 0.0
        self.duration_ms = 0.0

    def __enter__(self) -> RequestTimer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.duration_ms = (time.perf_counter() - self._start) * 1000
