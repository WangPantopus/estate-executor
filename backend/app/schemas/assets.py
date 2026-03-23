"""Asset schemas."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AssetStatus,
    AssetType,
    OwnershipType,
    TransferMechanism,
)

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    from .common import PaginationMeta
    from .tasks import DocumentBrief


class EntityBrief(BaseModel):
    """Brief entity reference for asset responses."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    name: str
    entity_type: str


class AssetCreate(BaseModel):
    """Schema for creating a new asset."""

    model_config = ConfigDict(strict=True)

    asset_type: AssetType
    title: str
    description: str | None = None
    institution: str | None = None
    account_number: str | None = None
    ownership_type: OwnershipType = OwnershipType.individual
    transfer_mechanism: TransferMechanism = TransferMechanism.probate
    date_of_death_value: Decimal | None = Field(None, max_digits=15, decimal_places=2)
    current_estimated_value: Decimal | None = Field(None, max_digits=15, decimal_places=2)
    metadata: dict[str, Any] | None = None


class AssetUpdate(BaseModel):
    """Schema for updating an asset. All fields optional."""

    model_config = ConfigDict(strict=True)

    asset_type: AssetType | None = None
    title: str | None = None
    description: str | None = None
    institution: str | None = None
    account_number: str | None = None
    ownership_type: OwnershipType | None = None
    transfer_mechanism: TransferMechanism | None = None
    status: AssetStatus | None = None
    date_of_death_value: Decimal | None = Field(None, max_digits=15, decimal_places=2)
    current_estimated_value: Decimal | None = Field(None, max_digits=15, decimal_places=2)
    final_appraised_value: Decimal | None = Field(None, max_digits=15, decimal_places=2)
    metadata: dict[str, Any] | None = None


class AssetListItem(BaseModel):
    """Asset item for list responses — includes doc count and entity briefs."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    matter_id: UUID
    asset_type: AssetType
    title: str
    description: str | None
    institution: str | None
    account_number_masked: str | None
    ownership_type: OwnershipType
    transfer_mechanism: TransferMechanism
    status: AssetStatus
    date_of_death_value: Decimal | None
    current_estimated_value: Decimal | None
    final_appraised_value: Decimal | None
    metadata: dict[str, Any] | None
    document_count: int
    entities: list[EntityBrief]
    created_at: datetime
    updated_at: datetime


class AssetListResponse(BaseModel):
    """Paginated list of assets."""

    model_config = ConfigDict(strict=True)

    data: list[AssetListItem]
    meta: PaginationMeta


class ValuationEntry(BaseModel):
    """A single valuation event from the asset's event history."""

    model_config = ConfigDict(strict=True)

    type: str
    value: Decimal
    notes: str | None
    recorded_at: datetime
    recorded_by: UUID | None


class AssetDetailResponse(BaseModel):
    """Full asset detail — includes documents, entities, and valuations history."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    matter_id: UUID
    asset_type: AssetType
    title: str
    description: str | None
    institution: str | None
    account_number_masked: str | None
    ownership_type: OwnershipType
    transfer_mechanism: TransferMechanism
    status: AssetStatus
    date_of_death_value: Decimal | None
    current_estimated_value: Decimal | None
    final_appraised_value: Decimal | None
    metadata: dict[str, Any] | None
    documents: list[DocumentBrief]
    entities: list[EntityBrief]
    valuations: list[ValuationEntry]
    created_at: datetime
    updated_at: datetime


class AssetLinkDocument(BaseModel):
    """Schema for linking a document to an asset."""

    model_config = ConfigDict(strict=True)

    document_id: UUID


class AssetValuation(BaseModel):
    """Schema for adding a valuation to an asset."""

    model_config = ConfigDict(strict=True)

    type: Literal["date_of_death", "current_estimate", "final_appraised"]
    value: Decimal = Field(..., max_digits=15, decimal_places=2)
    notes: str | None = None
