"""Distribution schemas — recording, listing, summaries."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DistributionType

from .common import PaginationMeta


class DistributionCreate(BaseModel):
    """Schema for recording a new distribution."""

    model_config = ConfigDict(strict=True)

    asset_id: UUID | None = None
    beneficiary_stakeholder_id: UUID
    amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    description: str
    distribution_type: DistributionType
    distribution_date: date
    notes: str | None = None


class DistributionResponse(BaseModel):
    """Schema for distribution response."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    matter_id: UUID
    asset_id: UUID | None
    asset_title: str | None = None
    beneficiary_stakeholder_id: UUID
    beneficiary_name: str = ""
    amount: Decimal | None
    description: str
    distribution_type: DistributionType
    distribution_date: date
    receipt_acknowledged: bool
    receipt_acknowledged_at: datetime | None
    notes: str | None
    created_at: datetime


class DistributionListResponse(BaseModel):
    """Paginated list of distributions."""

    model_config = ConfigDict(strict=True)

    data: list[DistributionResponse]
    meta: PaginationMeta


class BeneficiarySummaryItem(BaseModel):
    """Distribution summary for a single beneficiary."""

    model_config = ConfigDict(strict=True)

    stakeholder_id: UUID
    beneficiary_name: str
    total_distributed: Decimal
    distribution_count: int
    acknowledged_count: int
    pending_count: int


class DistributionSummaryResponse(BaseModel):
    """Overall distribution summary for a matter."""

    model_config = ConfigDict(strict=True)

    total_distributed: Decimal
    total_distributions: int
    total_acknowledged: int
    total_pending: int
    by_beneficiary: list[BeneficiarySummaryItem]
    by_type: dict[str, Decimal]
