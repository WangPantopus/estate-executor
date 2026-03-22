"""FastAPI dependency injection functions."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.events import EventLogger, event_logger


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Provide a transactional database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_redis():  # type: ignore[no-untyped-def]
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


def get_s3_client():  # type: ignore[no-untyped-def]
    """Return a boto3 S3 client configured from settings."""
    import boto3

    from app.core.config import settings

    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def get_event_logger() -> EventLogger:
    """Return the singleton EventLogger instance."""
    return event_logger
