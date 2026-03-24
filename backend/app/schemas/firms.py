"""Firm schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import FirmType, SubscriptionTier

from .common import PaginationMeta

# ─── White-label / branding config ───────────────────────────────────────────


class WhiteLabelConfig(BaseModel):
    """White-label branding configuration stored in firms.white_label JSONB."""

    model_config = ConfigDict(strict=True)

    logo_url: str | None = None
    logo_dark_url: str | None = None  # dark mode variant
    favicon_url: str | None = None
    primary_color: str | None = None  # hex e.g. "#1a73e8"
    secondary_color: str | None = None
    accent_color: str | None = None
    firm_display_name: str | None = None  # shown in portal header
    portal_welcome_text: str | None = None
    email_footer_text: str | None = None
    custom_domain: str | None = None  # e.g. "estates.smithlaw.com"
    custom_domain_verified: bool = False
    powered_by_visible: bool = True  # show "Powered by Estate Executor"


class WhiteLabelUpdate(BaseModel):
    """Partial update for white-label config."""

    model_config = ConfigDict(strict=True)

    logo_url: str | None = None
    logo_dark_url: str | None = None
    favicon_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    firm_display_name: str | None = None
    portal_welcome_text: str | None = None
    email_footer_text: str | None = None
    custom_domain: str | None = None
    powered_by_visible: bool | None = None


# ─── Firm CRUD schemas ───────────────────────────────────────────────────────


class FirmCreate(BaseModel):
    """Schema for creating a new firm."""

    model_config = ConfigDict(strict=True)

    name: str
    type: FirmType


class FirmUpdate(BaseModel):
    """Schema for updating a firm."""

    model_config = ConfigDict(strict=True)

    name: str | None = None
    type: FirmType | None = None
    settings: dict[str, Any] | None = None
    white_label: WhiteLabelUpdate | None = None


class FirmResponse(BaseModel):
    """Schema for firm response."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    name: str
    slug: str
    type: FirmType
    subscription_tier: SubscriptionTier
    settings: dict[str, Any] | None
    white_label: WhiteLabelConfig | None = None
    created_at: datetime
    updated_at: datetime


class FirmListResponse(BaseModel):
    """Paginated list of firms."""

    model_config = ConfigDict(strict=True)

    data: list[FirmResponse]
    meta: PaginationMeta


# ─── Logo upload ─────────────────────────────────────────────────────────────


class LogoUploadResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    upload_url: str
    logo_url: str
    field: str  # "logo_url" or "logo_dark_url" or "favicon_url"
