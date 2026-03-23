"""AI rate limiter — sliding-window rate limiting via Redis.

Enforces per-firm and per-matter rate limits on AI API calls to control
costs and prevent abuse.
"""

from __future__ import annotations

import logging
import time
from uuid import UUID

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Rate limits
FIRM_LIMIT_PER_HOUR = 100
MATTER_LIMIT_PER_HOUR = 20
_WINDOW_SECONDS = 3600

# Redis key prefixes
_FIRM_KEY_PREFIX = "ai_rate:firm:"
_MATTER_KEY_PREFIX = "ai_rate:matter:"

# Lazy-init sync Redis client
_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


class RateLimitExceeded(Exception):
    """Raised when an AI rate limit is exceeded."""

    def __init__(self, scope: str, limit: int, window_seconds: int = _WINDOW_SECONDS):
        self.scope = scope
        self.limit = limit
        self.window_seconds = window_seconds
        super().__init__(
            f"AI rate limit exceeded for {scope}: {limit} calls per {window_seconds}s"
        )


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


def _check_and_increment(key: str, limit: int) -> int:
    """Atomic sliding-window rate limit check using a Redis Lua script.

    Returns the current count after incrementing. Raises RateLimitExceeded
    if the limit would be exceeded.
    """
    r = _get_redis()
    now = time.time()
    window_start = now - _WINDOW_SECONDS
    ttl = _WINDOW_SECONDS + 60  # TTL slightly longer than window

    result = r.eval(_RATE_LIMIT_SCRIPT, 1, key, limit, now, window_start, ttl)

    if result == -1:
        raise RateLimitExceeded(scope=key, limit=limit)

    return int(result)


_CHECK_BOTH_SCRIPT = """
local firm_key = KEYS[1]
local matter_key = KEYS[2]
local firm_limit = tonumber(ARGV[1])
local matter_limit = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local window_start = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

-- Clean and check both limits BEFORE incrementing either
redis.call('ZREMRANGEBYSCORE', firm_key, 0, window_start)
redis.call('ZREMRANGEBYSCORE', matter_key, 0, window_start)

local firm_count = redis.call('ZCARD', firm_key)
local matter_count = redis.call('ZCARD', matter_key)

if firm_count >= firm_limit then
    return -1
end
if matter_count >= matter_limit then
    return -2
end

-- Both passed — now increment both atomically
redis.call('ZADD', firm_key, now, tostring(now) .. ':f')
redis.call('EXPIRE', firm_key, ttl)
redis.call('ZADD', matter_key, now, tostring(now) .. ':m')
redis.call('EXPIRE', matter_key, ttl)
return firm_count + 1
"""


def check_rate_limit(*, firm_id: UUID, matter_id: UUID) -> None:
    """Atomically check both firm-level and matter-level rate limits.

    Uses a single Lua script to check both limits before incrementing either,
    preventing asymmetric state on partial failures.
    """
    firm_key = f"{_FIRM_KEY_PREFIX}{firm_id}"
    matter_key = f"{_MATTER_KEY_PREFIX}{matter_id}"

    try:
        r = _get_redis()
        now = time.time()
        window_start = now - _WINDOW_SECONDS
        ttl = _WINDOW_SECONDS + 60

        result = r.eval(
            _CHECK_BOTH_SCRIPT, 2, firm_key, matter_key,
            FIRM_LIMIT_PER_HOUR, MATTER_LIMIT_PER_HOUR,
            now, window_start, ttl,
        )

        if result == -1:
            raise RateLimitExceeded(scope=firm_key, limit=FIRM_LIMIT_PER_HOUR)
        if result == -2:
            raise RateLimitExceeded(scope=matter_key, limit=MATTER_LIMIT_PER_HOUR)
    except RateLimitExceeded:
        raise
    except Exception:
        # Redis failures should not block AI processing — log and allow
        logger.warning("ai_rate_limit_check_failed", exc_info=True)


def get_usage(*, firm_id: UUID | None = None, matter_id: UUID | None = None) -> dict[str, int]:
    """Get current rate limit usage counts (for monitoring)."""
    result: dict[str, int] = {}
    try:
        r = _get_redis()
        now = time.time()
        window_start = now - _WINDOW_SECONDS

        if firm_id:
            key = f"{_FIRM_KEY_PREFIX}{firm_id}"
            r.zremrangebyscore(key, 0, window_start)
            result["firm_calls_this_hour"] = r.zcard(key)

        if matter_id:
            key = f"{_MATTER_KEY_PREFIX}{matter_id}"
            r.zremrangebyscore(key, 0, window_start)
            result["matter_calls_this_hour"] = r.zcard(key)
    except Exception:
        logger.warning("ai_rate_limit_get_usage_failed", exc_info=True)

    return result
