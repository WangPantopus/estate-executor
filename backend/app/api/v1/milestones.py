"""Milestone detection and configuration API routes."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.security import get_current_user, require_firm_member, require_stakeholder
from app.models.enums import StakeholderRole
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.schemas.auth import CurrentUser
from app.services import milestone_service

router = APIRouter()


class MilestoneStatusResponse(BaseModel):
    """Status of all milestones for a matter."""

    model_config = ConfigDict(strict=True)

    milestones: list[dict[str, Any]]


class MilestoneSettingUpdate(BaseModel):
    """Input for toggling auto-notification for a milestone."""

    model_config = ConfigDict(strict=True)

    milestone_key: str
    enabled: bool


# ---------------------------------------------------------------------------
# GET .../milestones — Get milestone status for a matter
# ---------------------------------------------------------------------------


@router.get("", response_model=MilestoneStatusResponse)
async def get_milestones(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> MilestoneStatusResponse:
    """Get the status of all defined milestones for a matter.

    Returns completion progress, achieved dates, and notification settings.
    """
    milestones = await milestone_service.get_milestone_status(
        db, matter_id=matter_id
    )
    return MilestoneStatusResponse(milestones=milestones)


# ---------------------------------------------------------------------------
# GET .../milestones/definitions — Get milestone definitions
# ---------------------------------------------------------------------------


@router.get("/definitions")
async def get_milestone_definitions(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
) -> dict[str, Any]:
    """Get all available milestone definitions."""
    return {
        "definitions": [
            {
                "key": m["key"],
                "title": m["title"],
                "description": m["description"],
                "phase": m["phase"].value if hasattr(m["phase"], "value") else m["phase"],
            }
            for m in milestone_service.MILESTONE_DEFINITIONS
        ]
    }


# ---------------------------------------------------------------------------
# PUT .../milestones/settings — Toggle auto-notification per milestone
# ---------------------------------------------------------------------------


@router.put("/settings")
async def update_milestone_settings(
    firm_id: UUID,
    matter_id: UUID,
    body: MilestoneSettingUpdate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Enable or disable auto-notifications for a specific milestone.

    Only matter admins can change milestone notification settings.
    """
    if stakeholder.role != StakeholderRole.matter_admin:
        raise PermissionDeniedError(
            detail="Only matter admins can change milestone notification settings"
        )

    settings = await milestone_service.update_milestone_settings(
        db,
        matter_id=matter_id,
        milestone_key=body.milestone_key,
        enabled=body.enabled,
        current_user=current_user,
    )
    return {"milestone_notifications": settings}
