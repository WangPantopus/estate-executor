"""Branding service — white-label configuration, logo upload, domain management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.core.config import settings
from app.core.events import event_logger
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.enums import ActorType, SubscriptionTier
from app.models.firms import Firm
from app.services import storage_service

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

# Default branding when white_label is not configured
DEFAULT_BRANDING = {
    "logo_url": None,
    "logo_dark_url": None,
    "favicon_url": None,
    "primary_color": "#1a2332",
    "secondary_color": "#c9a84c",
    "accent_color": "#3b82f6",
    "firm_display_name": None,
    "portal_welcome_text": None,
    "email_footer_text": None,
    "custom_domain": None,
    "custom_domain_verified": False,
    "powered_by_visible": True,
}


async def get_branding(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
) -> dict[str, Any]:
    """Get the resolved branding config for a firm.

    Merges firm's white_label with defaults.
    """
    result = await db.execute(select(Firm).where(Firm.id == firm_id))
    firm = result.scalar_one_or_none()
    if firm is None:
        raise NotFoundError(detail="Firm not found")

    branding = {**DEFAULT_BRANDING}
    if firm.white_label:
        branding.update({k: v for k, v in firm.white_label.items() if v is not None})

    # Use firm name as display name if not explicitly set
    if not branding.get("firm_display_name"):
        branding["firm_display_name"] = firm.name

    return branding


async def update_branding(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    updates: dict[str, Any],
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Update white-label branding configuration.

    Only enterprise or growth tiers can use white-label features.
    """
    result = await db.execute(select(Firm).where(Firm.id == firm_id))
    firm = result.scalar_one_or_none()
    if firm is None:
        raise NotFoundError(detail="Firm not found")

    # White-label requires growth or enterprise tier
    tier_value = firm.subscription_tier.value if hasattr(firm.subscription_tier, "value") else firm.subscription_tier
    if tier_value not in (
        SubscriptionTier.growth.value,
        SubscriptionTier.enterprise.value,
    ):
        raise PermissionDeniedError(
            detail="White-label branding requires Growth or Enterprise plan"
        )

    current_wl = dict(firm.white_label) if firm.white_label else {}
    changes: dict[str, Any] = {}

    for key, value in updates.items():
        if value is not None:
            old_val = current_wl.get(key)
            if old_val != value:
                changes[key] = {"old": old_val, "new": value}
                current_wl[key] = value

    if changes:
        firm.white_label = current_wl
        await db.flush()

        await event_logger.log(
            db,
            matter_id=firm_id,
            actor_id=current_user.user_id,
            actor_type=ActorType.user,
            entity_type="firm",
            entity_id=firm_id,
            action="branding_updated",
            changes=changes,
        )

    return await get_branding(db, firm_id=firm_id)


async def get_logo_upload_url(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    field: str = "logo_url",
    content_type: str = "image/png",
) -> dict[str, str]:
    """Generate a presigned upload URL for a logo/favicon.

    Returns dict with upload_url, logo_url (the public URL after upload),
    and field name.
    """
    valid_fields = {"logo_url", "logo_dark_url", "favicon_url"}
    if field not in valid_fields:
        from app.core.exceptions import ValidationError

        raise ValidationError(detail=f"Invalid field: {field}")

    ext = "png" if "png" in content_type else "jpg"
    storage_key = f"branding/{firm_id}/{field}.{ext}"

    upload_url = storage_service.generate_presigned_put_url(storage_key=storage_key, content_type=content_type)

    # The public URL for the logo after upload
    logo_url = f"{settings.backend_url}/api/v1/branding/{firm_id}/{field}.{ext}"

    return {
        "upload_url": upload_url,
        "logo_url": logo_url,
        "field": field,
    }


def get_email_branding(white_label: dict[str, Any] | None, firm_name: str) -> dict[str, Any]:
    """Build email template context from firm branding.

    Synchronous helper for use in Celery tasks.
    """
    branding = {**DEFAULT_BRANDING}
    if white_label:
        branding.update({k: v for k, v in white_label.items() if v is not None})

    return {
        "firm_name": branding.get("firm_display_name") or firm_name,
        "logo_url": branding.get("logo_url"),
        "primary_color": branding.get("primary_color", "#1a2332"),
        "accent_color": branding.get("accent_color", "#3b82f6"),
        "footer_text": branding.get("email_footer_text"),
        "powered_by_visible": branding.get("powered_by_visible", True),
    }


def get_pdf_branding(white_label: dict[str, Any] | None, firm_name: str) -> dict[str, Any]:
    """Build PDF report branding context from firm config.

    Synchronous helper for use in report generation.
    """
    branding = {**DEFAULT_BRANDING}
    if white_label:
        branding.update({k: v for k, v in white_label.items() if v is not None})

    primary = str(branding.get("primary_color", "#1a2332"))
    secondary = str(branding.get("secondary_color", "#c9a84c"))

    return {
        "firm_name": branding.get("firm_display_name") or firm_name,
        "logo_url": branding.get("logo_url"),
        "primary_color": _hex_to_rgb(primary),
        "secondary_color": _hex_to_rgb(secondary),
        "powered_by_visible": branding.get("powered_by_visible", True),
    }


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (26, 35, 50)  # fallback to NAVY
    try:
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )
    except ValueError:
        return (26, 35, 50)
