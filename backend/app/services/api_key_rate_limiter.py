"""Per-API-key rate limiter — Redis sliding-window implementation."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import redis

from app.core.config import settings
from app.core.exceptions import RateLimitError

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)

_KEY_PREFIX = "api_rate:key:"
_WINDOW_SECONDS = 60  # 1-minute sliding window

# Lazy-init sync Redis client (shared with AI rate limiter)
_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


_RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local now = tonumber(ARGV[2])
local window_start = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])

redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
local count = redis.call('ZCARD', key)

if count >= limit then
    return -1
end

redis.call('ZADD', key, now, tostring(now))
redis.call('EXPIRE', key, ttl)
return count + 1
"""


def check_api_key_rate_limit(*, key_id: UUID, limit_per_minute: int) -> dict[str, int]:
    """Check and increment rate limit for an API key.

    Returns dict with current count and limit.
    Raises RateLimitError (HTTP 429) if limit exceeded.
    """
    redis_key = f"{_KEY_PREFIX}{key_id}"

    try:
        r = _get_redis()
        now = time.time()
        window_start = now - _WINDOW_SECONDS
        ttl = _WINDOW_SECONDS + 10

        result = r.eval(
            _RATE_LIMIT_SCRIPT,
            1,
            redis_key,
            str(limit_per_minute),
            str(now),
            str(window_start),
            str(ttl),
        )

        count = int(result)  # type: ignore[arg-type]
        if count == -1:
            raise RateLimitError(
                detail=(f"API rate limit exceeded: {limit_per_minute} requests per minute")
            )

        return {
            "current": count,
            "limit": limit_per_minute,
            "remaining": limit_per_minute - count,
        }
    except RateLimitError:
        raise
    except Exception:
        logger.warning("api_key_rate_limit_check_failed", exc_info=True)
        return {"current": 0, "limit": limit_per_minute, "remaining": limit_per_minute}


def get_api_key_usage(*, key_id: UUID) -> dict[str, int]:
    """Get current rate limit usage for monitoring."""
    redis_key = f"{_KEY_PREFIX}{key_id}"
    try:
        r = _get_redis()
        now = time.time()
        window_start = now - _WINDOW_SECONDS
        r.zremrangebyscore(redis_key, 0, window_start)
        count = int(r.zcard(redis_key))  # type: ignore[arg-type]
        return {"requests_this_minute": count}
    except Exception:
        logger.warning("api_key_rate_limit_usage_failed", exc_info=True)
        return {"requests_this_minute": 0}
