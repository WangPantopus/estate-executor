"""Health check endpoints.

- GET /health          — shallow liveness probe (always 200 if process is up)
- GET /health/ready    — deep readiness probe (checks DB, Redis, S3, Claude API)
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Shallow liveness probe — returns 200 if the process is alive."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    """Deep readiness probe — verifies all critical dependencies.

    Returns 200 if all checks pass, 503 if any check fails.
    Each check includes its latency in milliseconds.
    """
    from fastapi.responses import JSONResponse

    checks: dict[str, dict[str, Any]] = {}
    overall_ok = True

    # ── PostgreSQL ─────────────────────────────────────────────────────
    checks["database"] = await _check_database()
    if checks["database"]["status"] != "ok":
        overall_ok = False

    # ── Redis ──────────────────────────────────────────────────────────
    checks["redis"] = await _check_redis()
    if checks["redis"]["status"] != "ok":
        overall_ok = False

    # ── S3 / MinIO ─────────────────────────────────────────────────────
    checks["storage"] = await _check_s3()
    if checks["storage"]["status"] != "ok":
        overall_ok = False

    # ── Claude API (Anthropic) ─────────────────────────────────────────
    checks["claude_api"] = await _check_claude_api()
    if checks["claude_api"]["status"] != "ok":
        overall_ok = False

    # ── Celery / Task Queue ────────────────────────────────────────────
    checks["task_queue"] = await _check_celery()
    if checks["task_queue"]["status"] != "ok":
        overall_ok = False

    result = {
        "status": "ok" if overall_ok else "degraded",
        "checks": checks,
    }

    status_code = 200 if overall_ok else 503
    return JSONResponse(content=result, status_code=status_code)


async def _check_database() -> dict[str, Any]:
    """Verify PostgreSQL connectivity via async session."""
    start = time.perf_counter()
    try:
        from sqlalchemy import text

        from app.core.database import async_session_factory

        async with async_session_factory() as session:
            row = await session.execute(text("SELECT 1"))
            row.scalar()
        latency = (time.perf_counter() - start) * 1000
        return {"status": "ok", "latency_ms": round(latency, 2)}
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        logger.error("health_check_failed", extra={"component": "database", "error": str(exc)})
        return {"status": "error", "latency_ms": round(latency, 2), "error": str(exc)}


async def _check_redis() -> dict[str, Any]:
    """Verify Redis connectivity with PING."""
    start = time.perf_counter()
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            pong = await r.ping()
            latency = (time.perf_counter() - start) * 1000
            if pong:
                return {"status": "ok", "latency_ms": round(latency, 2)}
            return {"status": "error", "latency_ms": round(latency, 2), "error": "PING returned False"}
        finally:
            await r.aclose()
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        logger.error("health_check_failed", extra={"component": "redis", "error": str(exc)})
        return {"status": "error", "latency_ms": round(latency, 2), "error": str(exc)}


async def _check_s3() -> dict[str, Any]:
    """Verify S3/MinIO connectivity by listing the bucket (HEAD)."""
    start = time.perf_counter()
    try:
        import boto3
        from botocore.config import Config as BotoConfig

        s3_kwargs: dict[str, Any] = {
            "service_name": "s3",
            "region_name": settings.aws_region,
            "aws_access_key_id": settings.aws_access_key_id,
            "aws_secret_access_key": settings.aws_secret_access_key,
            "config": BotoConfig(connect_timeout=5, read_timeout=5),
        }
        if settings.s3_endpoint_url:
            s3_kwargs["endpoint_url"] = settings.s3_endpoint_url

        client = boto3.client(**s3_kwargs)
        client.head_bucket(Bucket=settings.aws_s3_bucket)
        latency = (time.perf_counter() - start) * 1000
        return {"status": "ok", "latency_ms": round(latency, 2)}
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        logger.error("health_check_failed", extra={"component": "storage", "error": str(exc)})
        return {"status": "error", "latency_ms": round(latency, 2), "error": str(exc)}


async def _check_claude_api() -> dict[str, Any]:
    """Verify Anthropic API key is valid by counting available models."""
    start = time.perf_counter()
    if not settings.anthropic_api_key:
        return {"status": "error", "latency_ms": 0, "error": "ANTHROPIC_API_KEY not configured"}
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                # Send a minimal request — we expect a 400 (bad request body)
                # rather than 401 (invalid key). This validates the key without
                # consuming tokens.
            )
        latency = (time.perf_counter() - start) * 1000
        # 400 = key works but body is missing; 401/403 = bad key
        if resp.status_code in (400, 200):
            return {"status": "ok", "latency_ms": round(latency, 2)}
        return {
            "status": "error",
            "latency_ms": round(latency, 2),
            "error": f"Unexpected status {resp.status_code}",
        }
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        logger.error("health_check_failed", extra={"component": "claude_api", "error": str(exc)})
        return {"status": "error", "latency_ms": round(latency, 2), "error": str(exc)}


async def _check_celery() -> dict[str, Any]:
    """Verify Celery broker (Redis) is reachable via the Celery broker URL."""
    start = time.perf_counter()
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.celery_broker_url, decode_responses=True)
        try:
            pong = await r.ping()
            latency = (time.perf_counter() - start) * 1000
            if pong:
                return {"status": "ok", "latency_ms": round(latency, 2)}
            return {"status": "error", "latency_ms": round(latency, 2), "error": "Broker PING failed"}
        finally:
            await r.aclose()
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        logger.error("health_check_failed", extra={"component": "task_queue", "error": str(exc)})
        return {"status": "error", "latency_ms": round(latency, 2), "error": str(exc)}
