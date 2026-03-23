"""Matter management API routes."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from app.core.dependencies import get_db
from app.core.security import get_current_user, require_firm_member, require_stakeholder
from app.models.enums import FirmRole, MatterPhase, MatterStatus, StakeholderRole
from app.schemas.common import PaginationMeta, PaginationParams
from app.schemas.deadlines import DeadlineResponse
from app.schemas.events import EventResponse
from app.schemas.matters import (
    AssetSummary,
    MatterCreate,
    MatterDashboard,
    MatterListResponse,
    MatterResponse,
    MatterUpdate,
    TaskSummary,
)
from app.services import matter_service

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.firm_memberships import FirmMembership
    from app.models.stakeholders import Stakeholder
    from app.schemas.auth import CurrentUser

router = APIRouter()


# ---------------------------------------------------------------------------
# Portfolio view schema (route-local)
# ---------------------------------------------------------------------------


class PortfolioMatterItem(BaseModel):
    """Single matter with summary stats for portfolio view."""

    model_config = ConfigDict(strict=True)

    matter: MatterResponse
    total_task_count: int
    complete_task_count: int
    open_task_count: int
    overdue_task_count: int
    approaching_deadline_count: int
    next_deadline: date | None
    has_dispute: bool
    oldest_blocked_task_days: int | None
    risk_level: str  # "green" | "amber" | "red"


class PortfolioSummary(BaseModel):
    """Cross-matter aggregate summary for the portfolio header."""

    model_config = ConfigDict(strict=True)

    total_active_matters: int
    total_overdue_tasks: int
    approaching_deadlines_this_week: int
    matters_by_phase: dict[str, int]


class PortfolioResponse(BaseModel):
    """Paginated portfolio view response."""

    model_config = ConfigDict(strict=True)

    summary: PortfolioSummary
    data: list[PortfolioMatterItem]
    meta: PaginationMeta


# ---------------------------------------------------------------------------
# POST /firms/{firm_id}/matters — Create a new matter
# ---------------------------------------------------------------------------


@router.post("", response_model=MatterResponse, status_code=201)
async def create_matter(
    firm_id: UUID,
    body: MatterCreate,
    _membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatterResponse:
    """Create a new matter. Creator is automatically added as matter_admin stakeholder."""
    matter = await matter_service.create_matter(
        db,
        firm_id=firm_id,
        title=body.title,
        estate_type=body.estate_type,
        jurisdiction_state=body.jurisdiction_state,
        decedent_name=body.decedent_name,
        date_of_death=body.date_of_death,
        date_of_incapacity=body.date_of_incapacity,
        estimated_value=body.estimated_value,
        current_user=current_user,
    )
    return MatterResponse.model_validate(matter)


# ---------------------------------------------------------------------------
# GET /firms/{firm_id}/matters — List matters (or portfolio view)
# ---------------------------------------------------------------------------


@router.get("")
async def list_matters(
    firm_id: UUID,
    view: str | None = Query(None, description="Set to 'portfolio' for firm-level dashboard"),
    status: MatterStatus | None = Query(None),
    phase: MatterPhase | None = Query(None),
    search: str | None = Query(None, description="Search title or decedent name"),
    jurisdiction_state: str | None = Query(None, max_length=2),
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> MatterListResponse | PortfolioResponse:
    """List matters with filters and pagination.

    With ?view=portfolio (firm admins only), returns summary stats per matter.
    """
    if view == "portfolio":
        # Portfolio view — requires firm admin
        if membership.firm_role not in (FirmRole.owner, FirmRole.admin):
            from app.core.exceptions import PermissionDeniedError

            raise PermissionDeniedError(
                detail="Portfolio view requires firm admin access"
            )

        portfolio_data = await matter_service.get_portfolio(
            db,
            firm_id=firm_id,
            status=status,
            phase=phase,
            search=search,
            jurisdiction_state=jurisdiction_state,
            page=pagination.page,
            per_page=pagination.per_page,
        )
        items = portfolio_data["items"]
        total = portfolio_data["total"]
        summary = portfolio_data["summary"]

        return PortfolioResponse(
            summary=PortfolioSummary(**summary),
            data=[
                PortfolioMatterItem(
                    matter=MatterResponse.model_validate(item["matter"]),
                    total_task_count=item["total_task_count"],
                    complete_task_count=item["complete_task_count"],
                    open_task_count=item["open_task_count"],
                    overdue_task_count=item["overdue_task_count"],
                    approaching_deadline_count=item["approaching_deadline_count"],
                    next_deadline=item["next_deadline"],
                    has_dispute=item["has_dispute"],
                    oldest_blocked_task_days=item["oldest_blocked_task_days"],
                    risk_level=item["risk_level"],
                )
                for item in items
            ],
            meta=PaginationMeta(
                total=total,
                page=pagination.page,
                per_page=pagination.per_page,
                total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0,
            ),
        )

    # Standard list view
    matters, total = await matter_service.list_matters(
        db,
        firm_id=firm_id,
        current_user=current_user,
        status=status,
        phase=phase,
        search=search,
        jurisdiction_state=jurisdiction_state,
        page=pagination.page,
        per_page=pagination.per_page,
    )
    return MatterListResponse(
        data=[MatterResponse.model_validate(m) for m in matters],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0,
        ),
    )


# ---------------------------------------------------------------------------
# GET /firms/{firm_id}/matters/{matter_id} — Matter dashboard
# ---------------------------------------------------------------------------


@router.get("/{matter_id}", response_model=MatterDashboard)
async def get_matter_dashboard(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> MatterDashboard:
    """Get matter dashboard with aggregated data.

    Beneficiaries see a reduced dashboard (no detailed asset values or events).
    """
    matter = await matter_service.get_matter(db, matter_id=matter_id)

    dashboard_data = await matter_service.get_dashboard(
        db,
        matter_id=matter_id,
        stakeholder_role=stakeholder.role,
    )

    return MatterDashboard(
        matter=MatterResponse.model_validate(matter),
        task_summary=TaskSummary(**dashboard_data["task_summary"]),
        asset_summary=AssetSummary(**dashboard_data["asset_summary"]),
        stakeholder_count=dashboard_data["stakeholder_count"],
        upcoming_deadlines=[
            DeadlineResponse.model_validate(d) for d in dashboard_data["upcoming_deadlines"]
        ],
        recent_events=[
            EventResponse.model_validate(e) for e in dashboard_data["recent_events"]
        ],
    )


# ---------------------------------------------------------------------------
# PATCH /firms/{firm_id}/matters/{matter_id} — Update matter
# ---------------------------------------------------------------------------


@router.patch("/{matter_id}", response_model=MatterResponse)
async def update_matter(
    firm_id: UUID,
    matter_id: UUID,
    body: MatterUpdate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatterResponse:
    """Update matter details. Requires matter_admin or professional role."""
    if stakeholder.role not in (StakeholderRole.matter_admin, StakeholderRole.professional):
        from app.core.exceptions import PermissionDeniedError

        raise PermissionDeniedError(
            detail="Only matter admins and professionals can update matters"
        )

    updates = body.model_dump(exclude_unset=True)
    matter = await matter_service.update_matter(
        db,
        matter_id=matter_id,
        updates=updates,
        current_user=current_user,
    )
    return MatterResponse.model_validate(matter)


# ---------------------------------------------------------------------------
# POST /firms/{firm_id}/matters/{matter_id}/close — Close matter
# ---------------------------------------------------------------------------


@router.post("/{matter_id}/close", response_model=MatterResponse)
async def close_matter(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatterResponse:
    """Close a matter. All critical tasks must be complete or waived.

    Only matter_admin can close a matter (per permission model §7.2).
    """
    if stakeholder.role != StakeholderRole.matter_admin:
        from app.core.exceptions import PermissionDeniedError

        raise PermissionDeniedError(
            detail="Only matter admins can close matters"
        )

    matter = await matter_service.close_matter(
        db,
        matter_id=matter_id,
        current_user=current_user,
    )
    return MatterResponse.model_validate(matter)
