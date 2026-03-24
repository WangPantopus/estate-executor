"""Communication schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import CommunicationType, CommunicationVisibility

from .common import PaginationMeta


class CommunicationCreate(BaseModel):
    """Schema for creating a new communication."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "type": "message",
                    "subject": "Estate Update",
                    "body": "The probate petition has been filed.",
                    "visibility": "all_stakeholders",
                }
            ]
        },
    )

    type: CommunicationType
    subject: str | None = None
    body: str
    visibility: CommunicationVisibility | None = None
    visible_to: list[UUID] | None = None


class CommunicationResponse(BaseModel):
    """Schema for communication response."""

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "matter_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "sender_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                    "sender_name": "Jane Attorney",
                    "type": "message",
                    "subject": "Estate Update",
                    "body": "The probate petition has been filed.",
                    "visibility": "all_stakeholders",
                    "acknowledged_by": [],
                    "created_at": "2025-01-15T10:30:00Z",
                }
            ]
        },
    )

    id: UUID
    matter_id: UUID
    sender_id: UUID
    sender_name: str = ""  # Populated by service layer from sender relationship
    type: CommunicationType
    subject: str | None
    body: str
    visibility: CommunicationVisibility
    acknowledged_by: list[UUID] | None
    created_at: datetime

    # Dispute-specific fields (populated only for dispute_flag type)
    disputed_entity_type: str | None = None
    disputed_entity_id: UUID | None = None
    dispute_status: str | None = None
    dispute_resolution_note: str | None = None
    dispute_resolved_at: datetime | None = None
    dispute_resolved_by: UUID | None = None


class CommunicationListResponse(BaseModel):
    """Paginated list of communications."""

    model_config = ConfigDict(strict=True)

    data: list[CommunicationResponse]
    meta: PaginationMeta


class DisputeFlagCreate(BaseModel):
    """Schema for flagging a dispute on an entity."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "entity_type": "asset",
                    "entity_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "reason": "Disputed ownership of the property.",
                }
            ]
        },
    )

    entity_type: str
    entity_id: UUID
    reason: str


class DisputeStatusUpdate(BaseModel):
    """Schema for updating a dispute's status (under_review or resolved)."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "status": "resolved",
                    "resolution_note": "Ownership verified via title deed. Dispute closed.",
                }
            ]
        },
    )

    status: str  # "under_review" or "resolved"
    resolution_note: str  # Required for both transitions
