"""Entity schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EntityType, FundingStatus


class AssetBrief(BaseModel):
    """Brief asset reference for entity responses."""

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "title": "Primary Residence",
                    "asset_type": "real_estate",
                    "current_estimated_value": "900000.00",
                }
            ]
        },
    )

    id: UUID
    title: str
    asset_type: str
    current_estimated_value: Decimal | None = Field(None, max_digits=15, decimal_places=2)


class EntityCreate(BaseModel):
    """Schema for creating a new entity."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "entity_type": "revocable_trust",
                    "name": "Doe Family Revocable Trust",
                    "trustee": "Jane Doe",
                    "successor_trustee": "First National Bank",
                    "funding_status": "fully_funded",
                }
            ]
        },
    )

    entity_type: EntityType
    name: str
    trustee: str | None = None
    successor_trustee: str | None = None
    trigger_conditions: dict[str, Any] | None = None
    funding_status: FundingStatus | None = None
    distribution_rules: dict[str, Any] | None = None
    asset_ids: list[UUID] | None = None


class EntityUpdate(BaseModel):
    """Schema for updating an entity. All fields optional."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "name": "Doe Family Trust (Amended)",
                    "funding_status": "partially_funded",
                    "asset_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
                }
            ]
        },
    )

    entity_type: EntityType | None = None
    name: str | None = None
    trustee: str | None = None
    successor_trustee: str | None = None
    trigger_conditions: dict[str, Any] | None = None
    funding_status: FundingStatus | None = None
    distribution_rules: dict[str, Any] | None = None
    asset_ids: list[UUID] | None = None


class EntityResponse(BaseModel):
    """Schema for entity response."""

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "matter_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "entity_type": "revocable_trust",
                    "name": "Doe Family Revocable Trust",
                    "trustee": "Jane Doe",
                    "successor_trustee": "First National Bank",
                    "trigger_conditions": None,
                    "funding_status": "fully_funded",
                    "distribution_rules": None,
                    "metadata": {},
                    "assets": [],
                    "created_at": "2025-01-15T10:30:00Z",
                    "updated_at": "2025-01-15T10:30:00Z",
                }
            ]
        },
    )

    id: UUID
    matter_id: UUID
    entity_type: EntityType
    name: str
    trustee: str | None
    successor_trustee: str | None
    trigger_conditions: dict[str, Any] | None
    funding_status: FundingStatus
    distribution_rules: dict[str, Any] | None
    metadata: dict[str, Any] | None
    assets: list[AssetBrief]
    created_at: datetime
    updated_at: datetime


class FundingDetail(BaseModel):
    """Funding status detail for an entity."""

    model_config = ConfigDict(strict=True)

    entity_id: UUID
    entity_name: str
    funding_status: FundingStatus
    funded_count: int
    total_value: float | None = None


class EntityMapResponse(BaseModel):
    """Entity map showing entities and their asset relationships."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "entities": [],
                    "unassigned_assets": [],
                    "pour_over_candidates": [],
                    "funding_summary": [],
                }
            ]
        },
    )

    entities: list[EntityResponse]
    unassigned_assets: list[AssetBrief]
    pour_over_candidates: list[AssetBrief]
    funding_summary: list[FundingDetail]
