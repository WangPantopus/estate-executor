"""Global rate limiter — Redis sliding-window for all endpoints.

Provides per-user (authenticated) and per-IP (anonymous) rate limiting
with configurable limits per route tier.
"""

from __future__ import annotations

import logging
import re as _re
import time
from typing import TYPE_CHECKING

import redis

from app.core.config import settings
from app.core.exceptions import RateLimitError

if TYPE_CHECKING:
    from fastapi import Request

logger = logging.getLogger(__name__)

_KEY_PREFIX = "rl:"
_WINDOW_SECONDS = 60  # 1-minute sliding window

# Lazy-init sync Redis client
_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


# Lua script for atomic sliding window check-and-increment
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

redis.call('ZADD', key, now, tostring(now) .. ':' .. tostring(math.random(1000000)))
redis.call('EXPIRE', key, ttl)
return limit - count - 1
"""

# ---------------------------------------------------------------------------
# Tier definitions: (requests_per_minute)
# ---------------------------------------------------------------------------

def _get_tier_limits() -> dict[str, int]:
    """Return tier limits from settings, allowing runtime override via env vars."""
    return {
        "strict": settings.rate_limit_strict,
        "write": settings.rate_limit_write,
        "standard": settings.rate_limit_standard,
        "relaxed": settings.rate_limit_relaxed,
    }

# Route-suffix → tier mapping. We match on the *suffix* after the firm/matter
# prefix to avoid false-positive matches on "/api/v1/firms/".
_UUID = r"[0-9a-f\-]{36}"

_ROUTE_TIER_PATTERNS: list[tuple[_re.Pattern[str], str]] = [
    # Strict tier — auth, privacy, SSO
    (_re.compile(r"^/api/v1/auth(/|$)"), "strict"),
    (_re.compile(rf"^/api/v1/firms/{_UUID}/privacy(/|$)"), "strict"),
    (_re.compile(rf"^/api/v1/firms/{_UUID}/sso(/|$)"), "strict"),
    # Relaxed tier — templates (health is skipped entirely in middleware)
    (_re.compile(r"^/api/v1/templates(/|$)"), "relaxed"),
]


def _resolve_tier(path: str, method: str) -> str:
    """Determine the rate-limit tier for a request."""
    for pattern, tier in _ROUTE_TIER_PATTERNS:
        if pattern.search(path):
            return tier

    # Method-based fallback
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return "write"
    return "standard"


def _get_identifier(request: Request) -> str:
    """Return a rate-limit key identifier: user_id if authenticated, else client IP."""
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    # Fallback to IP
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    return f"ip:{ip}"


def check_rate_limit(request: Request) -> dict[str, int]:
    """Check and increment rate limit for a request.

    Returns dict with limit, remaining, and reset info.
    Raises RateLimitError (HTTP 429) if limit exceeded.
    """
    identifier = _get_identifier(request)
    tier = _resolve_tier(request.url.path, request.method)
    tier_limits = _get_tier_limits()
    limit = tier_limits[tier]

    redis_key = f"{_KEY_PREFIX}{tier}:{identifier}"

    try:
        r = _get_redis()
        now = time.time()
        window_start = now - _WINDOW_SECONDS
        ttl = _WINDOW_SECONDS + 10

        remaining = r.eval(
            _RATE_LIMIT_SCRIPT,
            1,
            redis_key,
            str(limit),
            str(now),
            str(window_start),
            str(ttl),
        )

        remaining = int(remaining)  # type: ignore[arg-type]
        if remaining == -1:
            raise RateLimitError(
                detail=f"Rate limit exceeded: {limit} requests per minute"
            )

        return {
            "limit": limit,
            "remaining": remaining,
        }
    except RateLimitError:
        raise
    except Exception:
        logger.warning("rate_limit_check_failed", exc_info=True)
        # Fail open: allow request if Redis is unavailable
        return {"limit": limit, "remaining": limit}
