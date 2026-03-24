"""Privacy request schemas for GDPR/CCPA compliance."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PrivacyRequestCreate(BaseModel):
    """Create a privacy request."""

    model_config = ConfigDict(strict=True)

    request_type: str = Field(..., description="data_export or data_deletion")
    reason: str | None = Field(None, max_length=1000)


class PrivacyRequestReview(BaseModel):
    """Admin review of a privacy request."""

    model_config = ConfigDict(strict=True)

    action: str = Field(..., description="approve or reject")
    note: str | None = Field(None, max_length=1000)


class PrivacyRequestResponse(BaseModel):
    """Privacy request response."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    firm_id: UUID
    user_id: UUID
    request_type: str
    status: str
    reason: str | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    completed_at: datetime | None = None
    export_storage_key: str | None = None
    deletion_summary: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    # User info (populated from relationship)
    user_email: str | None = None
    user_name: str | None = None


class PrivacyRequestListResponse(BaseModel):
    """Paginated list of privacy requests."""

    model_config = ConfigDict(strict=True)

    data: list[PrivacyRequestResponse]
    total: int
    page: int
    per_page: int
