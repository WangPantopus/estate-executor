"""Distribution Ledger API routes."""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.security import get_current_user, require_firm_member, require_stakeholder
from app.models.distributions import Distribution
from app.models.enums import StakeholderRole
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.schemas.auth import CurrentUser
from app.schemas.common import PaginationMeta, PaginationParams
from app.schemas.distributions import (
    BeneficiarySummaryItem,
    DistributionCreate,
    DistributionListResponse,
    DistributionResponse,
    DistributionSummaryResponse,
)
from app.services import distribution_service

router = APIRouter()

_WRITE_ROLES = {StakeholderRole.matter_admin, StakeholderRole.professional}


def _dist_to_response(dist: Distribution) -> DistributionResponse:
    """Convert a Distribution ORM object to DistributionResponse."""
    return DistributionResponse(
        id=dist.id,
        matter_id=dist.matter_id,
        asset_id=dist.asset_id,
        asset_title=dist.asset.title if dist.asset else None,
        beneficiary_stakeholder_id=dist.beneficiary_stakeholder_id,
        beneficiary_name=dist.beneficiary.full_name if dist.beneficiary else "",
        amount=dist.amount,
        description=dist.description,
        distribution_type=dist.distribution_type,
        distribution_date=dist.distribution_date,
        receipt_acknowledged=dist.receipt_acknowledged,
        receipt_acknowledged_at=dist.receipt_acknowledged_at,
        notes=dist.notes,
        created_at=dist.created_at,
    )


# ---------------------------------------------------------------------------
# POST — Record distribution
# ---------------------------------------------------------------------------


@router.post("", response_model=DistributionResponse, status_code=201)
async def record_distribution(
    firm_id: UUID,
    matter_id: UUID,
    body: DistributionCreate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DistributionResponse:
    """Record a new distribution. Requires matter_admin or professional role."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(
            detail="Only matter admins and professionals can record distributions"
        )

    dist = await distribution_service.record_distribution(
        db,
        matter_id=matter_id,
        asset_id=body.asset_id,
        beneficiary_stakeholder_id=body.beneficiary_stakeholder_id,
        amount=body.amount,
        description=body.description,
        distribution_type=body.distribution_type,
        distribution_date=body.distribution_date,
        notes=body.notes,
        sender_stakeholder=stakeholder,
        current_user=current_user,
    )
    return _dist_to_response(dist)


# ---------------------------------------------------------------------------
# GET — List distributions
# ---------------------------------------------------------------------------


@router.get("", response_model=DistributionListResponse)
async def list_distributions(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    pagination: PaginationParams = Depends(),
    beneficiary_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> DistributionListResponse:
    """List distributions for a matter."""
    distributions, total = await distribution_service.list_distributions(
        db,
        matter_id=matter_id,
        page=pagination.page,
        per_page=pagination.per_page,
        beneficiary_id=beneficiary_id,
    )

    return DistributionListResponse(
        data=[_dist_to_response(d) for d in distributions],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=max(1, math.ceil(total / pagination.per_page)),
        ),
    )


# ---------------------------------------------------------------------------
# POST — Acknowledge receipt
# ---------------------------------------------------------------------------


@router.post("/{dist_id}/acknowledge", response_model=DistributionResponse)
async def acknowledge_receipt(
    firm_id: UUID,
    matter_id: UUID,
    dist_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DistributionResponse:
    """Beneficiary acknowledges receipt of a distribution."""
    dist = await distribution_service.acknowledge_receipt(
        db,
        dist_id=dist_id,
        matter_id=matter_id,
        stakeholder=stakeholder,
        current_user=current_user,
    )
    return _dist_to_response(dist)


# ---------------------------------------------------------------------------
# GET — Summary
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=DistributionSummaryResponse)
async def get_distribution_summary(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> DistributionSummaryResponse:
    """Get distribution summary by beneficiary and type."""
    data = await distribution_service.get_distribution_summary(
        db, matter_id=matter_id
    )
    return DistributionSummaryResponse(
        total_distributed=data["total_distributed"],
        total_distributions=data["total_distributions"],
        total_acknowledged=data["total_acknowledged"],
        total_pending=data["total_pending"],
        by_beneficiary=[BeneficiarySummaryItem(**b) for b in data["by_beneficiary"]],
        by_type=data["by_type"],
    )
