"""Enterprise SSO service — configure, verify, auto-provision, enforce."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.events import event_logger
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.models.enums import ActorType, FirmRole, SubscriptionTier
from app.models.firm_memberships import FirmMembership
from app.models.firms import Firm
from app.models.sso_configs import SSOConfig

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.users import User
    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)


# ─── CRUD ────────────────────────────────────────────────────────────────────


async def get_sso_config(db: AsyncSession, *, firm_id: uuid.UUID) -> SSOConfig | None:
    result = await db.execute(select(SSOConfig).where(SSOConfig.firm_id == firm_id))
    return result.scalar_one_or_none()


async def get_sso_config_or_404(db: AsyncSession, *, firm_id: uuid.UUID) -> SSOConfig:
    config = await get_sso_config(db, firm_id=firm_id)
    if config is None:
        raise NotFoundError(detail="SSO not configured for this firm")
    return config


async def create_sso_config(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    data: dict[str, Any],
    current_user: CurrentUser,
) -> SSOConfig:
    """Create or replace SSO configuration for a firm."""
    # Enterprise tier required
    await _require_enterprise(db, firm_id)

    existing = await get_sso_config(db, firm_id=firm_id)
    if existing:
        raise ConflictError(detail="SSO already configured. Use update or delete first.")

    protocol = data.get("protocol", "saml")
    _validate_config(protocol, data)

    config = SSOConfig(
        firm_id=firm_id,
        protocol=protocol,
        saml_metadata_url=data.get("saml_metadata_url"),
        saml_metadata_xml=data.get("saml_metadata_xml"),
        oidc_discovery_url=data.get("oidc_discovery_url"),
        oidc_client_id=data.get("oidc_client_id"),
        oidc_client_secret=data.get("oidc_client_secret"),
        enforce_sso=data.get("enforce_sso", False),
        auto_provision=data.get("auto_provision", True),
        default_role=data.get("default_role", "member"),
        allowed_domains=data.get("allowed_domains", []),
        configured_by=current_user.user_id,
    )

    # Parse SAML metadata if URL provided
    if protocol == "saml" and config.saml_metadata_url:
        await _parse_saml_metadata(config)

    # Create Auth0 enterprise connection
    auth0_conn = await _create_auth0_connection(config, firm_id)
    if auth0_conn:
        config.auth0_connection_id = auth0_conn.get("id")
        config.auth0_connection_name = auth0_conn.get("name")

    db.add(config)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=firm_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="sso_config",
        entity_id=config.id,
        action="created",
        metadata={"protocol": protocol},
    )
    return config


async def update_sso_config(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    updates: dict[str, Any],
    current_user: CurrentUser,
) -> SSOConfig:
    config = await get_sso_config_or_404(db, firm_id=firm_id)

    changes: dict[str, Any] = {}
    for key, value in updates.items():
        if value is not None and hasattr(config, key):
            old = getattr(config, key)
            if old != value:
                changes[key] = {"old": str(old), "new": str(value)}
                setattr(config, key, value)

    if changes:
        # Re-parse SAML metadata if URL changed
        if "saml_metadata_url" in changes and config.saml_metadata_url:
            await _parse_saml_metadata(config)

        await db.flush()

        await event_logger.log(
            db,
            matter_id=firm_id,
            actor_id=current_user.user_id,
            actor_type=ActorType.user,
            entity_type="sso_config",
            entity_id=config.id,
            action="updated",
            changes=changes,
        )

    return config


async def delete_sso_config(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
) -> None:
    config = await get_sso_config_or_404(db, firm_id=firm_id)

    # Delete Auth0 connection if exists
    if config.auth0_connection_id:
        await _delete_auth0_connection(config.auth0_connection_id)

    await event_logger.log(
        db,
        matter_id=firm_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="sso_config",
        entity_id=config.id,
        action="deleted",
    )

    await db.delete(config)
    await db.flush()


async def enable_sso(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
) -> SSOConfig:
    config = await get_sso_config_or_404(db, firm_id=firm_id)
    if not config.auth0_connection_id:
        raise ValidationError(detail="SSO connection must be verified before enabling")
    config.enabled = True
    await db.flush()
    return config


async def disable_sso(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
) -> SSOConfig:
    config = await get_sso_config_or_404(db, firm_id=firm_id)
    config.enabled = False
    config.enforce_sso = False
    await db.flush()
    return config


# ─── SSO login URL ───────────────────────────────────────────────────────────


async def get_sso_login_url(db: AsyncSession, *, firm_id: uuid.UUID) -> dict[str, str]:
    """Get the SSO login URL for a firm's Auth0 connection."""
    config = await get_sso_config_or_404(db, firm_id=firm_id)
    if not config.enabled or not config.auth0_connection_name:
        raise ValidationError(detail="SSO is not enabled for this firm")

    login_url = (
        f"https://{settings.auth0_domain}/authorize"
        f"?response_type=code"
        f"&client_id={settings.auth0_client_id}"
        f"&connection={config.auth0_connection_name}"
        f"&redirect_uri={settings.frontend_url}/auth/callback"
        f"&scope=openid profile email"
    )

    return {
        "login_url": login_url,
        "connection_name": config.auth0_connection_name,
        "protocol": config.protocol,
    }


# ─── SSO enforcement check ──────────────────────────────────────────────────


async def check_sso_enforcement(db: AsyncSession, *, email: str) -> dict[str, Any] | None:
    """Check if the user's email domain requires SSO login.

    Returns minimal SSO info if enforcement applies, None otherwise.
    Called during normal login to redirect SSO-enforced users.

    NOTE: This is called unauthenticated — only return the minimum info
    the login page needs to redirect. Never expose firm_id/firm_name.
    """
    domain = email.split("@")[-1].lower() if "@" in email else ""
    if not domain:
        return None

    # Find any SSO config with matching allowed domain and enforcement
    result = await db.execute(
        select(SSOConfig).where(
            SSOConfig.enforce_sso.is_(True),
            SSOConfig.enabled.is_(True),
        )
    )
    configs = list(result.scalars().all())

    for config in configs:
        allowed = [d.lower() for d in (config.allowed_domains or [])]
        if domain in allowed:
            # Only return what the login page needs — no firm details
            return {
                "connection_name": config.auth0_connection_name,
                "protocol": config.protocol,
            }

    return None


# ─── Auto-provisioning ──────────────────────────────────────────────────────


async def auto_provision_sso_user(
    db: AsyncSession,
    *,
    user: User,
    auth0_connection_name: str | None,
) -> FirmMembership | None:
    """Auto-provision a new SSO user into their firm.

    Called after successful SSO login when the user doesn't have
    a firm membership yet.
    """
    if not auth0_connection_name:
        return None

    # Find SSO config by Auth0 connection name
    result = await db.execute(
        select(SSOConfig).where(
            SSOConfig.auth0_connection_name == auth0_connection_name,
            SSOConfig.auto_provision.is_(True),
        )
    )
    config = result.scalar_one_or_none()
    if config is None:
        return None

    # Check domain allowlist
    domain = user.email.split("@")[-1].lower()
    allowed = [d.lower() for d in (config.allowed_domains or [])]
    if allowed and domain not in allowed:
        logger.info(
            "sso_auto_provision_domain_rejected",
            extra={"email": user.email, "domain": domain},
        )
        return None

    # Check if already a member
    existing = await db.execute(
        select(FirmMembership).where(
            FirmMembership.firm_id == config.firm_id,
            FirmMembership.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        return None

    # Create membership
    role = (
        FirmRole(config.default_role)
        if config.default_role in FirmRole.__members__
        else FirmRole.member
    )
    membership = FirmMembership(
        firm_id=config.firm_id,
        user_id=user.id,
        firm_role=role,
    )
    db.add(membership)

    # Update last login
    config.last_login_at = datetime.now(UTC)
    await db.flush()

    logger.info(
        "sso_user_auto_provisioned",
        extra={
            "user_id": str(user.id),
            "firm_id": str(config.firm_id),
            "role": role.value,
        },
    )

    await event_logger.log(
        db,
        matter_id=config.firm_id,
        actor_id=None,
        actor_type=ActorType.system,
        entity_type="firm_membership",
        entity_id=membership.id,
        action="auto_provisioned",
        metadata={"email": user.email, "role": role.value, "via": "sso"},
    )

    return membership


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _require_enterprise(db: AsyncSession, firm_id: uuid.UUID) -> None:
    result = await db.execute(select(Firm).where(Firm.id == firm_id))
    firm = result.scalar_one_or_none()
    if firm is None:
        raise NotFoundError(detail="Firm not found")

    tier_value = firm.subscription_tier.value if hasattr(firm.subscription_tier, "value") else firm.subscription_tier
    if tier_value != SubscriptionTier.enterprise.value:
        raise PermissionDeniedError(detail="Enterprise SSO requires an Enterprise subscription")


def _validate_config(protocol: str, data: dict[str, Any]) -> None:
    if protocol == "saml":
        if not data.get("saml_metadata_url") and not data.get("saml_metadata_xml"):
            raise ValidationError(detail="SAML requires either metadata_url or metadata_xml")
    elif protocol == "oidc":
        if not data.get("oidc_discovery_url"):
            raise ValidationError(detail="OIDC requires a discovery URL")
        if not data.get("oidc_client_id"):
            raise ValidationError(detail="OIDC requires a client ID")
    else:
        raise ValidationError(detail=f"Unsupported protocol: {protocol}")

    # Validate allowed_domains
    import re

    domains = data.get("allowed_domains", [])
    if len(domains) > 50:
        raise ValidationError(detail="Maximum 50 allowed domains")
    domain_re = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$")
    for d in domains:
        if not isinstance(d, str) or not domain_re.match(d) or len(d) > 255:
            raise ValidationError(detail=f"Invalid domain: {d!r}. Use format: example.com")


async def _parse_saml_metadata(config: SSOConfig) -> None:
    """Fetch and parse SAML metadata URL to extract entity ID and SSO URL."""
    if not config.saml_metadata_url:
        return

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(config.saml_metadata_url)
            resp.raise_for_status()

            # Validate response size (max 1MB) to prevent DoS
            content_length = len(resp.content)
            if content_length > 1_048_576:
                raise ValidationError(detail="SAML metadata too large (max 1MB)")

            xml_text = resp.text

        config.saml_metadata_xml = xml_text

        # Basic XML parsing for entity ID and SSO URL
        import re

        entity_match = re.search(r'entityID="([^"]+)"', xml_text)
        if entity_match:
            config.saml_entity_id = entity_match.group(1)

        sso_match = re.search(r'SingleSignOnService[^>]*Location="([^"]+)"', xml_text)
        if sso_match:
            config.saml_sso_url = sso_match.group(1)

    except httpx.HTTPError:
        logger.warning("saml_metadata_fetch_failed", exc_info=True)
        raise ValidationError(
            detail="Failed to fetch SAML metadata from the provided URL"
        ) from None


async def _create_auth0_connection(config: SSOConfig, firm_id: uuid.UUID) -> dict[str, Any] | None:
    """Create an enterprise connection in Auth0 via Management API.

    Returns the connection object or None if creation fails.
    """
    if not settings.auth0_domain or not settings.auth0_client_secret:
        logger.warning("auth0_not_configured_for_sso")
        return None

    # Get Management API token
    token = await _get_auth0_management_token()
    if not token:
        return None

    conn_name = f"sso-{str(firm_id)[:8]}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if config.protocol == "saml":
                body: dict[str, Any] = {
                    "name": conn_name,
                    "strategy": "samlp",
                    "options": {
                        "signInEndpoint": config.saml_sso_url or "",
                        "signingCert": config.saml_certificate or "",
                        "entityId": config.saml_entity_id or "",
                    },
                }
                if config.saml_metadata_url:
                    body["options"]["metadataUrl"] = config.saml_metadata_url
            else:
                body = {
                    "name": conn_name,
                    "strategy": "oidc",
                    "options": {
                        "discovery_url": config.oidc_discovery_url or "",
                        "client_id": config.oidc_client_id or "",
                        "client_secret": config.oidc_client_secret or "",
                        "scope": "openid profile email",
                        "type": "front_channel",
                    },
                }

            resp = await client.post(
                f"https://{settings.auth0_domain}/api/v2/connections",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            return dict(resp.json())

    except httpx.HTTPError:
        logger.error("auth0_create_connection_failed", exc_info=True)
        return None


async def _delete_auth0_connection(connection_id: str) -> None:
    """Delete an Auth0 enterprise connection."""
    token = await _get_auth0_management_token()
    if not token:
        return

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.delete(
                f"https://{settings.auth0_domain}/api/v2/connections/{connection_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError:
        logger.warning("auth0_delete_connection_failed", exc_info=True)


async def _get_auth0_management_token() -> str | None:
    """Get an Auth0 Management API token via client credentials."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"https://{settings.auth0_domain}/oauth/token",
                json={
                    "client_id": settings.auth0_client_id,
                    "client_secret": settings.auth0_client_secret,
                    "audience": f"https://{settings.auth0_domain}/api/v2/",
                    "grant_type": "client_credentials",
                },
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            return data.get("access_token")
    except httpx.HTTPError:
        logger.error("auth0_management_token_failed", exc_info=True)
        return None
