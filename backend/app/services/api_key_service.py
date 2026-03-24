"""API key service — generation, hashing, validation, management."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select, update

from app.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    UnauthorizedError,
)
from app.models.api_keys import APIKey
from app.models.enums import SubscriptionTier

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

# Key format: ee_live_<32 hex chars>  (total ~40 chars)
_KEY_PREFIX_LEN = 12  # "ee_live_xxxx" — first 12 chars stored for display


def _generate_raw_key() -> str:
    """Generate a cryptographically random API key."""
    random_part = secrets.token_hex(24)  # 48 hex chars
    return f"ee_live_{random_part}"


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash of the raw key for storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _extract_prefix(raw_key: str) -> str:
    return raw_key[:_KEY_PREFIX_LEN]


# ─── CRUD ────────────────────────────────────────────────────────────────────


async def list_api_keys(db: AsyncSession, *, firm_id: uuid.UUID) -> list[APIKey]:
    result = await db.execute(
        select(APIKey).where(APIKey.firm_id == firm_id).order_by(APIKey.created_at.desc())
    )
    return list(result.scalars().all())


async def create_api_key(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    name: str,
    description: str | None = None,
    scopes: list[str] | None = None,
    rate_limit_per_minute: int = 60,
    expires_at: datetime | None = None,
    current_user: CurrentUser,
) -> tuple[APIKey, str]:
    """Create a new API key. Returns (model, raw_key).

    The raw key is returned ONLY at creation time.
    """
    await _require_enterprise(db, firm_id)

    raw_key = _generate_raw_key()
    key_obj = APIKey(
        firm_id=firm_id,
        name=name,
        description=description,
        key_prefix=_extract_prefix(raw_key),
        key_hash=_hash_key(raw_key),
        scopes=scopes or ["read"],
        rate_limit_per_minute=rate_limit_per_minute,
        expires_at=expires_at,
        created_by=current_user.user_id,
    )
    db.add(key_obj)
    await db.flush()

    logger.info(
        "api_key_created",
        extra={"firm_id": str(firm_id), "key_id": str(key_obj.id)},
    )
    return key_obj, raw_key


async def get_api_key(db: AsyncSession, *, key_id: uuid.UUID, firm_id: uuid.UUID) -> APIKey:
    result = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.firm_id == firm_id))
    key = result.scalar_one_or_none()
    if key is None:
        raise NotFoundError(detail="API key not found")
    return key


async def revoke_api_key(db: AsyncSession, *, key_id: uuid.UUID, firm_id: uuid.UUID) -> APIKey:
    key = await get_api_key(db, key_id=key_id, firm_id=firm_id)
    key.is_active = False
    await db.flush()
    logger.info("api_key_revoked", extra={"key_id": str(key_id)})
    return key


async def delete_api_key(db: AsyncSession, *, key_id: uuid.UUID, firm_id: uuid.UUID) -> None:
    key = await get_api_key(db, key_id=key_id, firm_id=firm_id)
    await db.delete(key)
    await db.flush()


async def regenerate_api_key(
    db: AsyncSession, *, key_id: uuid.UUID, firm_id: uuid.UUID
) -> tuple[APIKey, str]:
    """Regenerate an API key — invalidates old key, issues new one."""
    key = await get_api_key(db, key_id=key_id, firm_id=firm_id)
    raw_key = _generate_raw_key()
    key.key_prefix = _extract_prefix(raw_key)
    key.key_hash = _hash_key(raw_key)
    key.total_requests = 0
    key.last_used_at = None
    await db.flush()
    return key, raw_key


# ─── Authentication ──────────────────────────────────────────────────────────


async def authenticate_api_key(db: AsyncSession, *, raw_key: str) -> APIKey:
    """Validate a raw API key and return the associated APIKey model.

    Raises UnauthorizedError if invalid, expired, or revoked.
    """
    key_hash = _hash_key(raw_key)
    result = await db.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    key = result.scalar_one_or_none()

    if key is None:
        raise UnauthorizedError(detail="Invalid API key")

    if not key.is_active:
        raise UnauthorizedError(detail="API key has been revoked")

    if key.expires_at and key.expires_at < datetime.now(UTC):
        raise UnauthorizedError(detail="API key has expired")

    # Update usage stats (fire-and-forget style — don't block)
    await db.execute(
        update(APIKey)
        .where(APIKey.id == key.id)
        .values(
            last_used_at=datetime.now(UTC),
            total_requests=APIKey.total_requests + 1,
        )
    )

    return key


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _require_enterprise(db: AsyncSession, firm_id: uuid.UUID) -> None:
    from app.models.firms import Firm

    result = await db.execute(select(Firm).where(Firm.id == firm_id))
    firm = result.scalar_one_or_none()
    if firm is None:
        raise NotFoundError(detail="Firm not found")
    tier = firm.subscription_tier
    if hasattr(tier, "value"):
        tier = tier.value
    if tier != SubscriptionTier.enterprise.value:
        raise PermissionDeniedError(detail="API keys require an Enterprise subscription")
