"""API key authentication dependency — separate from JWT auth.

Usage:
    @router.get("/endpoint")
    async def my_endpoint(
        api_key: APIKey = Depends(require_api_key),
    ):
        ...

Reads the key from the X-API-Key header, validates it, checks
rate limits, and returns the associated APIKey model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader

from app.core.database import async_session_factory
from app.services.api_key_rate_limiter import check_api_key_rate_limit
from app.services.api_key_service import authenticate_api_key

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.api_keys import APIKey

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def _get_db_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def require_api_key(
    request: Request,
    raw_key: str = Depends(_api_key_header),
    db: AsyncSession = Depends(_get_db_session),
) -> APIKey:
    """Authenticate via X-API-Key header and enforce rate limits.

    Sets rate-limit headers on the response:
      X-RateLimit-Limit, X-RateLimit-Remaining
    """
    key = await authenticate_api_key(db, raw_key=raw_key)

    # Per-key rate limiting
    rate_info = check_api_key_rate_limit(key_id=key.id, limit_per_minute=key.rate_limit_per_minute)

    # Store rate info for response headers (middleware picks this up)
    request.state.rate_limit_info = rate_info

    return key
