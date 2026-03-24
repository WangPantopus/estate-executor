"""Redis caching layer for frequently accessed, rarely mutated data.

Provides a generic cache interface plus domain-specific helpers for:
- Firm settings
- User permissions / stakeholder roles
- Task template registry

All cache operations are fail-open: if Redis is unavailable, we fall
through to the database/filesystem without raising.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redis client singleton
# ---------------------------------------------------------------------------

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    # NOTE: This returns a synchronous Redis client used from an async (FastAPI)
    # context. Each call will briefly block the event loop for the duration of
    # the Redis I/O (typically < 1ms on a local/VPC connection; up to 2s on
    # timeout). Migrating to redis.asyncio with async cache helpers is the
    # correct long-term fix, but requires updating all call sites.
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis_client


# ---------------------------------------------------------------------------
# Generic cache helpers
# ---------------------------------------------------------------------------

_KEY_PREFIX = "cache:"


def _key(namespace: str, *parts: str) -> str:
    return f"{_KEY_PREFIX}{namespace}:{':'.join(parts)}"


def cache_get(namespace: str, *parts: str) -> Any | None:
    """Fetch a cached JSON value. Returns None on miss or Redis failure."""
    try:
        r = _get_redis()
        raw = r.get(_key(namespace, *parts))
        if raw is None:
            return None
        return json.loads(raw)  # type: ignore[arg-type]
    except Exception:
        logger.debug("Cache miss (error) for %s:%s", namespace, parts)
        return None


def cache_set(
    namespace: str,
    *parts: str,
    value: Any,
    ttl_seconds: int = 300,
) -> None:
    """Store a JSON-serializable value with TTL. Fails silently."""
    try:
        r = _get_redis()
        r.setex(_key(namespace, *parts), ttl_seconds, json.dumps(value, default=str))
    except Exception:
        logger.debug("Cache set failed for %s:%s", namespace, parts)


def cache_delete(namespace: str, *parts: str) -> None:
    """Delete a single cache key. Fails silently."""
    try:
        r = _get_redis()
        r.delete(_key(namespace, *parts))
    except Exception:
        logger.debug("Cache delete failed for %s:%s", namespace, parts)


def cache_invalidate_pattern(namespace: str, *parts: str) -> None:
    """Delete all keys matching a pattern. Use sparingly — SCAN-based.

    Example: cache_invalidate_pattern("permissions", str(matter_id))
    """
    try:
        r = _get_redis()
        pattern = _key(namespace, *parts, "*")
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor=cursor, match=pattern, count=100)  # type: ignore[misc]
            if keys:
                r.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.debug("Cache invalidate_pattern failed for %s:%s", namespace, parts)


# ---------------------------------------------------------------------------
# Domain-specific: Firm settings
# ---------------------------------------------------------------------------

_FIRM_SETTINGS_NS = "firm_settings"
_FIRM_SETTINGS_TTL = 600  # 10 minutes


def get_cached_firm_settings(firm_id: str) -> dict[str, Any] | None:
    """Get firm settings from cache."""
    return cache_get(_FIRM_SETTINGS_NS, firm_id)


def set_cached_firm_settings(firm_id: str, settings_data: dict[str, Any]) -> None:
    """Cache firm settings."""
    cache_set(_FIRM_SETTINGS_NS, firm_id, value=settings_data, ttl_seconds=_FIRM_SETTINGS_TTL)


def invalidate_firm_settings(firm_id: str) -> None:
    """Invalidate cached firm settings after update."""
    cache_delete(_FIRM_SETTINGS_NS, firm_id)


# ---------------------------------------------------------------------------
# Domain-specific: User permissions (stakeholder role per matter)
# ---------------------------------------------------------------------------

_PERMISSIONS_NS = "permissions"
_PERMISSIONS_TTL = 300  # 5 minutes


def get_cached_user_permissions(
    user_id: str,
    matter_id: str,
) -> dict[str, Any] | None:
    """Get cached stakeholder role + permissions for a user on a matter."""
    return cache_get(_PERMISSIONS_NS, user_id, matter_id)


def set_cached_user_permissions(
    user_id: str,
    matter_id: str,
    permissions_data: dict[str, Any],
) -> None:
    """Cache user permissions for a matter."""
    cache_set(
        _PERMISSIONS_NS,
        user_id,
        matter_id,
        value=permissions_data,
        ttl_seconds=_PERMISSIONS_TTL,
    )


def invalidate_user_permissions(matter_id: str) -> None:
    """Invalidate all cached permissions for a matter (e.g., after role change).

    NOTE: The SCAN-then-DELETE pattern used by cache_invalidate_pattern is
    inherently racy — permission entries written between the SCAN and the DELETE
    will survive invalidation. The 5-minute TTL (_PERMISSIONS_TTL) is the upper
    bound on staleness. For a role revocation that must take immediate effect,
    prefer invalidate_user_permissions_for_user() when the specific user is known,
    which uses a single atomic DEL rather than SCAN+DEL.
    """
    cache_invalidate_pattern(_PERMISSIONS_NS, "*", matter_id)


def invalidate_user_permissions_for_user(user_id: str, matter_id: str) -> None:
    """Invalidate cached permissions for a specific user on a matter."""
    cache_delete(_PERMISSIONS_NS, user_id, matter_id)


# ---------------------------------------------------------------------------
# Domain-specific: Task template registry
# ---------------------------------------------------------------------------

_TEMPLATES_NS = "templates"
_TEMPLATES_TTL = 3600  # 1 hour — templates rarely change


def get_cached_templates(
    estate_type: str,
    state: str,
    flags_key: str,
) -> list[dict[str, Any]] | None:
    """Get cached merged template set for an estate_type+state+flags combo."""
    return cache_get(_TEMPLATES_NS, estate_type, state, flags_key)


def set_cached_templates(
    estate_type: str,
    state: str,
    flags_key: str,
    templates: list[dict[str, Any]],
) -> None:
    """Cache merged template set."""
    cache_set(
        _TEMPLATES_NS,
        estate_type,
        state,
        flags_key,
        value=templates,
        ttl_seconds=_TEMPLATES_TTL,
    )


def invalidate_all_templates() -> None:
    """Invalidate all cached template sets (e.g., after admin edits templates)."""
    cache_invalidate_pattern(_TEMPLATES_NS)


# ---------------------------------------------------------------------------
# Domain-specific: Dashboard aggregation (short-lived)
# ---------------------------------------------------------------------------

_DASHBOARD_NS = "dashboard"
_DASHBOARD_TTL = 60  # 1 minute — dashboard data changes frequently


def get_cached_dashboard(matter_id: str, role: str) -> dict[str, Any] | None:
    """Get cached dashboard data for a matter+role."""
    return cache_get(_DASHBOARD_NS, matter_id, role)


def set_cached_dashboard(
    matter_id: str,
    role: str,
    dashboard_data: dict[str, Any],
) -> None:
    """Cache dashboard aggregation results."""
    cache_set(
        _DASHBOARD_NS,
        matter_id,
        role,
        value=dashboard_data,
        ttl_seconds=_DASHBOARD_TTL,
    )


def invalidate_dashboard(matter_id: str) -> None:
    """Invalidate dashboard cache for a matter (after any mutation)."""
    cache_invalidate_pattern(_DASHBOARD_NS, matter_id)


# ---------------------------------------------------------------------------
# Domain-specific: Portfolio aggregation (short-lived)
# ---------------------------------------------------------------------------

_PORTFOLIO_NS = "portfolio"
_PORTFOLIO_TTL = 120  # 2 minutes


def get_cached_portfolio(firm_id: str, cache_key: str) -> dict[str, Any] | None:
    """Get cached portfolio data."""
    return cache_get(_PORTFOLIO_NS, firm_id, cache_key)


def set_cached_portfolio(
    firm_id: str,
    cache_key: str,
    portfolio_data: dict[str, Any],
) -> None:
    """Cache portfolio aggregation results."""
    cache_set(
        _PORTFOLIO_NS,
        firm_id,
        cache_key,
        value=portfolio_data,
        ttl_seconds=_PORTFOLIO_TTL,
    )


def invalidate_portfolio(firm_id: str) -> None:
    """Invalidate portfolio cache for a firm."""
    cache_invalidate_pattern(_PORTFOLIO_NS, firm_id)
