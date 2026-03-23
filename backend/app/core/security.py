"""JWT validation, auth dependencies, encryption, and permission checking."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import jwt
from cachetools import TTLCache
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import Depends, Request
from fastapi.security import OAuth2AuthorizationCodeBearer
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import NotFoundError, PermissionDeniedError, UnauthorizedError
from app.models.enums import StakeholderRole
from app.models.firm_memberships import FirmMembership
from app.models.matters import Matter
from app.models.stakeholders import Stakeholder
from app.models.users import User
from app.schemas.auth import CurrentUser, FirmMembershipBrief, TokenPayload

# ---------------------------------------------------------------------------
# OAuth2 scheme
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"https://{settings.auth0_domain}/authorize" if settings.auth0_domain else "",
    tokenUrl=f"https://{settings.auth0_domain}/oauth/token" if settings.auth0_domain else "",
    auto_error=True,
)

# ---------------------------------------------------------------------------
# JWKS cache — keys cached for 24 hours
# ---------------------------------------------------------------------------

_jwks_cache: TTLCache[str, dict[str, Any]] = TTLCache(maxsize=4, ttl=86400)


def _get_signing_key(token: str) -> jwt.PyJWK:
    """Fetch Auth0 JWKS and return the key matching the token's kid."""
    jwks_url = settings.auth0_jwks_url
    if "jwks" not in _jwks_cache:
        jwks_client = jwt.PyJWKClient(jwks_url)
        _jwks_cache["jwks"] = jwks_client.get_jwk_set().keys
        _jwks_cache["client"] = jwks_client
    client: jwt.PyJWKClient = _jwks_cache["client"]
    return client.get_signing_key_from_jwt(token)


# ---------------------------------------------------------------------------
# JWT verification
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Mock auth user map for E2E tests
# ---------------------------------------------------------------------------

_MOCK_USERS: dict[str, dict[str, str]] = {
    "admin": {"sub": "auth0|e2e-admin", "email": "admin@e2e-test.local"},
    "professional": {"sub": "auth0|e2e-professional", "email": "pro@e2e-test.local"},
    "beneficiary": {"sub": "auth0|e2e-beneficiary", "email": "beneficiary@e2e-test.local"},
    "readOnly": {"sub": "auth0|e2e-readOnly", "email": "readonly@e2e-test.local"},
}


async def verify_jwt(token: str) -> TokenPayload:
    """Verify and decode a JWT token from Auth0.

    - Fetches Auth0 JWKS (cached for 24h via cachetools)
    - Validates JWT signature, expiration, audience, issuer
    - Returns decoded payload as TokenPayload schema

    When E2E_MOCK_AUTH is enabled, accepts tokens of the form
    ``e2e-mock-token-<userKey>`` and returns a synthetic payload.
    """
    # Mock auth bypass for E2E tests
    if settings.e2e_mock_auth and token.startswith("e2e-mock-token-"):
        user_key = token.removeprefix("e2e-mock-token-")
        mock = _MOCK_USERS.get(user_key)
        if mock is None:
            raise UnauthorizedError(detail=f"Unknown mock user: {user_key}")
        return TokenPayload(
            sub=mock["sub"],
            email=mock["email"],
            firm_ids=[],
            roles={},
        )

    try:
        signing_key = _get_signing_key(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=settings.auth0_algorithms,
            audience=settings.auth0_api_audience,
            issuer=settings.auth0_issuer,
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError(detail="Token has expired") from None
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError(detail=f"Invalid token: {exc}") from exc

    return TokenPayload(
        sub=payload["sub"],
        email=payload.get("email", payload.get(f"{settings.auth0_api_audience}/email", "")),
        firm_ids=payload.get("firm_ids", []),
        roles=payload.get("roles", {}),
    )


# ---------------------------------------------------------------------------
# get_current_user dependency
# ---------------------------------------------------------------------------

# Avoid circular import: get_db is defined in dependencies.py but that
# module must not import from security. We re-use the same session factory.
from app.core.database import async_session_factory  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


async def _get_db_session() -> AsyncGenerator[AsyncSession]:
    """Provide an async session for auth dependencies.

    Separate from get_db in dependencies.py to avoid circular imports.
    Does not set RLS variables (auth runs before tenant context is known).
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(_get_db_session),
) -> CurrentUser:
    """Verify JWT, look up user by auth_provider_id, return CurrentUser.

    Auto-creates the user record on first login (provisioning).
    """
    payload = await verify_jwt(token)

    # Look up user by auth_provider_id (sub claim)
    result = await db.execute(
        select(User)
        .options(selectinload(User.firm_memberships))
        .where(User.auth_provider_id == payload.sub)
    )
    user = result.scalar_one_or_none()

    # First login provisioning
    if user is None:
        user = User(
            auth_provider_id=payload.sub,
            email=payload.email,
            full_name=payload.email.split("@")[0],
        )
        db.add(user)
        await db.flush()
        # Reload with relationships
        result = await db.execute(
            select(User).options(selectinload(User.firm_memberships)).where(User.id == user.id)
        )
        user = result.scalar_one()

    return CurrentUser(
        user_id=user.id,
        email=user.email,
        firm_memberships=[
            FirmMembershipBrief(firm_id=m.firm_id, firm_role=m.firm_role.value)
            for m in user.firm_memberships
        ],
    )


# ---------------------------------------------------------------------------
# require_firm_member dependency
# ---------------------------------------------------------------------------


async def require_firm_member(
    firm_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(_get_db_session),
) -> FirmMembership:
    """Verify user is a member of the specified firm.

    Returns 404 (not 403) to avoid confirming firm existence.
    """
    result = await db.execute(
        select(FirmMembership).where(
            FirmMembership.firm_id == firm_id,
            FirmMembership.user_id == current_user.user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise NotFoundError(detail="Firm not found")
    return membership


# ---------------------------------------------------------------------------
# require_stakeholder dependency
# ---------------------------------------------------------------------------


async def require_stakeholder(
    matter_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(_get_db_session),
) -> Stakeholder:
    """Check if user is a stakeholder on this matter.

    Falls back to checking firm membership on the matter's owning firm.
    Returns 404 if no access.
    """
    # Direct stakeholder lookup
    result = await db.execute(
        select(Stakeholder).where(
            Stakeholder.matter_id == matter_id,
            Stakeholder.user_id == current_user.user_id,
        )
    )
    stakeholder = result.scalar_one_or_none()
    if stakeholder is not None:
        return stakeholder

    # Fallback: check if user is a firm member of the matter's firm
    result = await db.execute(select(Matter.firm_id).where(Matter.id == matter_id))
    firm_id = result.scalar_one_or_none()
    if firm_id is None:
        raise NotFoundError(detail="Matter not found")

    result = await db.execute(
        select(FirmMembership).where(
            FirmMembership.firm_id == firm_id,
            FirmMembership.user_id == current_user.user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise NotFoundError(detail="Matter not found")

    # Firm members get a synthetic stakeholder with matter_admin permissions
    # Create a transient stakeholder object (not persisted)
    synthetic = Stakeholder(
        id=None,
        matter_id=matter_id,
        user_id=current_user.user_id,
        email=current_user.email,
        full_name="",
        role=StakeholderRole.matter_admin,
    )
    # Mark as transient so we don't accidentally persist it
    from sqlalchemy.orm import make_transient

    make_transient(synthetic)
    return synthetic


# ---------------------------------------------------------------------------
# Role-based permission map (from design doc §7.2)
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[StakeholderRole, list[str]] = {
    StakeholderRole.matter_admin: [
        "matter:read",
        "matter:write",
        "matter:close",
        "task:read",
        "task:write",
        "task:assign",
        "task:complete",
        "asset:read",
        "asset:write",
        "entity:read",
        "entity:write",
        "document:read",
        "document:upload",
        "document:download",
        "stakeholder:invite",
        "stakeholder:manage",
        "communication:read",
        "communication:write",
        "event:read",
        "ai:trigger",
        "report:generate",
    ],
    StakeholderRole.professional: [
        "matter:read",
        "task:read",
        "task:write",
        "task:assign",
        "task:complete",
        "asset:read",
        "asset:write",
        "entity:read",
        "entity:write",
        "document:read",
        "document:upload",
        "document:download",
        "communication:read",
        "communication:write",
        "event:read",
        "ai:trigger",
        "report:generate",
    ],
    StakeholderRole.executor_trustee: [
        "matter:read",
        "task:read:assigned",
        "task:complete:assigned",
        "asset:read",
        "document:read:linked",
        "document:upload",
        "communication:read",
        "communication:write",
    ],
    StakeholderRole.beneficiary: [
        "matter:read:summary",
        "task:read:milestones",
        "document:read:shared",
        "communication:read:visible",
    ],
    StakeholderRole.read_only: [
        "matter:read:summary",
        "task:read:milestones",
    ],
}


def _has_permission(role: StakeholderRole, required: str) -> bool:
    """Check if a role has the required permission.

    Supports hierarchical matching: "task:read" grants "task:read:assigned".
    """
    permissions = ROLE_PERMISSIONS.get(role, [])
    for perm in permissions:
        if perm == required:
            return True
        # "task:read" is a superset of "task:read:assigned"
        if required.startswith(perm + ":"):
            return True
    return False


def require_permission(permission: str) -> Callable[..., Any]:
    """Return a FastAPI dependency that checks the resolved
    stakeholder has the required permission."""

    async def _check(
        request: Request,
        stakeholder: Stakeholder = Depends(require_stakeholder),
    ) -> Stakeholder:
        if not _has_permission(stakeholder.role, permission):
            raise PermissionDeniedError(detail="Insufficient permissions")
        return stakeholder

    return _check


# ---------------------------------------------------------------------------
# Field-level encryption (AES-256-GCM)
# ---------------------------------------------------------------------------


def _get_encryption_key() -> bytes:
    """Return the 32-byte AES key derived from the master key setting."""
    key_hex = settings.encryption_master_key
    if not key_hex:
        raise ValueError("ENCRYPTION_MASTER_KEY is not configured")
    key = bytes.fromhex(key_hex)
    if len(key) != 32:
        raise ValueError("ENCRYPTION_MASTER_KEY must be 64 hex characters (32 bytes)")
    return key


def encrypt_field(plaintext: str) -> bytes:
    """Encrypt a string field using AES-256-GCM.

    Returns nonce (12 bytes) || ciphertext+tag.
    """
    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ciphertext


def decrypt_field(ciphertext: bytes) -> str:
    """Decrypt a field encrypted with encrypt_field.

    Expects nonce (12 bytes) || ciphertext+tag.
    """
    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = ciphertext[:12]
    encrypted = ciphertext[12:]
    plaintext = aesgcm.decrypt(nonce, encrypted, None)
    return plaintext.decode("utf-8")
