"""Firm schemas."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from app.models.enums import FirmType, SubscriptionTier

    from .common import PaginationMeta


class FirmCreate(BaseModel):
    """Schema for creating a new firm."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "name": "Smith & Associates",
                    "type": "law_firm",
                }
            ]
        },
    )

    name: str
    type: FirmType


class FirmUpdate(BaseModel):
    """Schema for updating a firm."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "name": "Smith & Partners",
                    "type": "law_firm",
                    "settings": {"timezone": "US/Eastern"},
                }
            ]
        },
    )

    name: str | None = None
    type: FirmType | None = None
    settings: dict[str, Any] | None = None


class FirmResponse(BaseModel):
    """Schema for firm response."""

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "name": "Smith & Associates",
                    "slug": "smith-associates",
                    "type": "law_firm",
                    "subscription_tier": "professional",
                    "settings": {},
                    "created_at": "2025-01-15T10:30:00Z",
                    "updated_at": "2025-01-15T10:30:00Z",
                }
            ]
        },
    )

    id: UUID
    name: str
    slug: str
    type: FirmType
    subscription_tier: SubscriptionTier
    settings: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class FirmListResponse(BaseModel):
    """Paginated list of firms."""

    model_config = ConfigDict(strict=True)

    data: list[FirmResponse]
    meta: PaginationMeta
