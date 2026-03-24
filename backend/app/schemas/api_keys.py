"""Pydantic schemas for API key management."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class APIKeyCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str
    description: str | None = None
    scopes: list[str] = ["read"]
    rate_limit_per_minute: int = 60
    expires_at: datetime | None = None


class APIKeyResponse(BaseModel):
    """API key response — never includes the hash or raw key."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    firm_id: UUID
    name: str
    description: str | None = None
    key_prefix: str
    scopes: list[str]
    rate_limit_per_minute: int
    is_active: bool
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    created_by: UUID
    total_requests: int
    created_at: datetime
    updated_at: datetime


class APIKeyCreatedResponse(BaseModel):
    """Returned only at creation — includes the raw key once."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    key: APIKeyResponse
    raw_key: str  # Only shown once!
