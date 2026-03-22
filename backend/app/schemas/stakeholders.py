"""Stakeholder schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import InviteStatus, StakeholderRole

from .common import PaginationMeta


class StakeholderInvite(BaseModel):
    """Schema for inviting a stakeholder to a matter."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "email": "beneficiary@example.com",
                    "full_name": "Jane Doe",
                    "role": "beneficiary",
                    "relationship": "spouse",
                }
            ]
        },
    )

    email: EmailStr
    full_name: str
    role: StakeholderRole
    relationship: str | None = None


class StakeholderUpdate(BaseModel):
    """Schema for updating a stakeholder."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "role": "executor_trustee",
                    "relationship": "child",
                    "notification_preferences": {"email": True, "sms": False},
                }
            ]
        },
    )

    role: StakeholderRole | None = None
    relationship: str | None = None
    notification_preferences: dict | None = None


class StakeholderResponse(BaseModel):
    """Schema for stakeholder response."""

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "matter_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "user_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                    "email": "beneficiary@example.com",
                    "full_name": "Jane Doe",
                    "role": "beneficiary",
                    "relationship": "spouse",
                    "invite_status": "accepted",
                    "created_at": "2025-01-15T10:30:00Z",
                }
            ]
        },
    )

    id: UUID
    matter_id: UUID
    user_id: UUID | None
    email: str
    full_name: str
    role: StakeholderRole
    relationship: str | None
    invite_status: InviteStatus
    created_at: datetime


class StakeholderListResponse(BaseModel):
    """Paginated list of stakeholders."""

    model_config = ConfigDict(strict=True)

    data: list[StakeholderResponse]
    meta: PaginationMeta
