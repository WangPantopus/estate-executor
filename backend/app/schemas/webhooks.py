"""Pydantic schemas for webhook management."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WebhookCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    url: str
    events: list[str]
    description: str | None = None


class WebhookUpdate(BaseModel):
    model_config = ConfigDict(strict=True)

    url: str | None = None
    events: list[str] | None = None
    description: str | None = None
    is_active: bool | None = None


class WebhookResponse(BaseModel):
    """Webhook response — secret is masked for security."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    firm_id: UUID
    url: str
    description: str | None = None
    # Secret is only shown at creation and after rotation
    events: list[str]
    is_active: bool
    last_triggered_at: datetime | None = None
    failure_count: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class WebhookCreatedResponse(BaseModel):
    """Returned at creation and after secret rotation — includes secret once."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    firm_id: UUID
    url: str
    description: str | None = None
    secret: str  # Only exposed here
    events: list[str]
    is_active: bool
    last_triggered_at: datetime | None = None
    failure_count: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class WebhookDeliveryResponse(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    webhook_id: UUID
    event_type: str
    payload: dict[str, Any]
    status_code: int | None = None
    response_body: str | None = None
    error_message: str | None = None
    success: bool
    duration_ms: int | None = None
    attempt: int
    created_at: datetime


class SupportedEventsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    events: list[str]
