"""FastAPI dependency injection functions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from app.core.database import async_session_factory
from app.core.events import EventLogger, event_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import Request
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_db(request: Request) -> AsyncGenerator[AsyncSession]:
    """Provide a transactional database session.

    If firm_id was extracted by TenantIsolationMiddleware, executes
    SET LOCAL to enable PostgreSQL Row-Level Security policies.
    """
    async with async_session_factory() as session:
        try:
            # Set RLS variable if firm_id is available from middleware
            firm_id = getattr(request.state, "firm_id", None)
            if firm_id:
                await session.execute(
                    text("SET LOCAL app.current_firm_id = :fid"),
                    {"fid": str(firm_id)},
                )

            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Module-level S3 client (lazy singleton — boto3 clients are thread-safe)
_s3_client: Any = None


def get_s3_client() -> Any:
    """Return a boto3 S3 client configured from settings.

    Uses a module-level singleton to avoid creating a new client per request.
    boto3 clients manage their own connection pools and are thread-safe.
    """
    global _s3_client
    if _s3_client is None:
        import boto3

        from app.core.config import settings

        _s3_client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
    return _s3_client


async def get_redis() -> AsyncGenerator[Any]:
    """Return a Redis connection from the pool.

    Lazily imports redis to avoid hard dependency when Redis is not available.
    """
    import redis.asyncio as aioredis

    from app.core.config import settings

    pool = aioredis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)
    client = aioredis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.aclose()


def get_event_logger() -> EventLogger:
    """Return the singleton EventLogger instance."""
    return event_logger
