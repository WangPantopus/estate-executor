"""Pydantic schemas for integration endpoints (Clio and future providers)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ─── Integration connection ──────────────────────────────────────────────────


class IntegrationConnectionResponse(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    firm_id: UUID
    provider: str
    status: str
    external_account_id: str | None = None
    external_account_name: str | None = None
    last_sync_at: datetime | None = None
    last_sync_status: str
    last_sync_error: str | None = None
    settings: dict = {}
    connected_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class IntegrationListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    connections: list[IntegrationConnectionResponse]


# ─── OAuth flow ──────────────────────────────────────────────────────────────


class OAuthInitResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    authorize_url: str
    state: str


# ─── Sync requests / responses ───────────────────────────────────────────────


class SyncRequest(BaseModel):
    """Trigger a sync for a specific resource type."""

    model_config = ConfigDict(strict=True)

    resource: Literal[
        "matters",
        "time_entries",
        "contacts",
        "distributions",
        "transactions",
        "account_balances",
    ]
    direction: Literal["push", "pull", "bidirectional"] = "bidirectional"
    matter_id: UUID | None = None


class SyncResultResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    resource: str
    direction: str
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = []
    synced_at: datetime | None = None


class SyncStatusResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    last_sync_at: datetime | None = None
    last_sync_status: str
    last_sync_error: str | None = None
    matters_synced: int = 0
    time_entries_synced: int = 0
    contacts_synced: int = 0


# ─── Integration settings ───────────────────────────────────────────────────


class ClioSettingsUpdate(BaseModel):
    """Configurable settings for the Clio integration."""

    model_config = ConfigDict(strict=True)

    auto_sync_matters: bool | None = None
    auto_sync_time_entries: bool | None = None
    auto_sync_contacts: bool | None = None
    sync_interval_minutes: int | None = None
    default_practice_area: str | None = None
    matter_status_mapping: dict[str, str] | None = None


class DisconnectResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    disconnected: bool = True
    provider: str
