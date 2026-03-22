"""Asset schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AssetStatus,
    AssetType,
    OwnershipType,
    TransferMechanism,
)

from .common import PaginationMeta
from .tasks import DocumentBrief


class EntityBrief(BaseModel):
    """Brief entity reference for asset responses."""

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "name": "Doe Family Trust",
                    "entity_type": "revocable_trust",
                }
            ]
        },
    )

    id: UUID
    name: str
    entity_type: str


class AssetCreate(BaseModel):
    """Schema for creating a new asset."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "asset_type": "real_estate",
                    "title": "Primary Residence",
                    "description": "123 Main St, Los Angeles, CA",
                    "institution": None,
                    "ownership_type": "individual",
                    "transfer_mechanism": "probate",
                    "date_of_death_value": "850000.00",
                    "current_estimated_value": "900000.00",
                }
            ]
        },
    )

    asset_type: AssetType
    title: str
    description: str | None = None
    institution: str | None = None
    ownership_type: OwnershipType | None = None
    transfer_mechanism: TransferMechanism | None = None
    date_of_death_value: Decimal | None = Field(
        None, max_digits=15, decimal_places=2
    )
    current_estimated_value: Decimal | None = Field(
        None, max_digits=15, decimal_places=2
    )
    metadata: dict | None = None


class AssetUpdate(BaseModel):
    """Schema for updating an asset. All fields optional."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "Primary Residence (Updated)",
                    "current_estimated_value": "925000.00",
                    "status": "valued",
                }
            ]
        },
    )

    asset_type: AssetType | None = None
    title: str | None = None
    description: str | None = None
    institution: str | None = None
    ownership_type: OwnershipType | None = None
    transfer_mechanism: TransferMechanism | None = None
    status: AssetStatus | None = None
    date_of_death_value: Decimal | None = Field(
        None, max_digits=15, decimal_places=2
    )
    current_estimated_value: Decimal | None = Field(
        None, max_digits=15, decimal_places=2
    )
    final_appraised_value: Decimal | None = Field(
        None, max_digits=15, decimal_places=2
    )
    metadata: dict | None = None


class AssetResponse(BaseModel):
    """Schema for asset response."""

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "matter_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "asset_type": "real_estate",
                    "title": "Primary Residence",
                    "description": "123 Main St, Los Angeles, CA",
                    "institution": None,
                    "ownership_type": "individual",
                    "transfer_mechanism": "probate",
                    "status": "discovered",
                    "date_of_death_value": "850000.00",
                    "current_estimated_value": "900000.00",
                    "final_appraised_value": None,
                    "metadata": {},
                    "documents": [],
                    "entities": [],
                    "created_at": "2025-01-15T10:30:00Z",
                    "updated_at": "2025-01-15T10:30:00Z",
                }
            ]
        },
    )

    id: UUID
    matter_id: UUID
    asset_type: AssetType
    title: str
    description: str | None
    institution: str | None
    ownership_type: OwnershipType
    transfer_mechanism: TransferMechanism
    status: AssetStatus
    date_of_death_value: Decimal | None
    current_estimated_value: Decimal | None
    final_appraised_value: Decimal | None
    metadata: dict | None
    documents: list[DocumentBrief]
    entities: list[EntityBrief]
    created_at: datetime
    updated_at: datetime


class AssetListResponse(BaseModel):
    """Paginated list of assets."""

    model_config = ConfigDict(strict=True)

    data: list[AssetResponse]
    meta: PaginationMeta
