"""Enterprise SSO configuration API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.security import get_current_user, require_firm_member
from app.models.enums import FirmRole
from app.models.firm_memberships import FirmMembership
from app.schemas.auth import CurrentUser
from app.schemas.sso import (
    SSOConfigCreate,
    SSOConfigResponse,
    SSOConfigUpdate,
    SSOLoginUrlResponse,
)
from app.services import sso_service

router = APIRouter()


def _require_owner(membership: FirmMembership) -> None:
    if membership.firm_role != FirmRole.owner:
        raise PermissionDeniedError(detail="Only firm owners can manage SSO configuration")


# ─── GET /firms/{firm_id}/sso — Get SSO config ──────────────────────────────


@router.get("", response_model=SSOConfigResponse | None)
async def get_sso_config(
    firm_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> SSOConfigResponse | None:
    """Get SSO configuration for a firm. Returns null if not configured."""
    config = await sso_service.get_sso_config(db, firm_id=firm_id)
    if config is None:
        return None
    return SSOConfigResponse.model_validate(config)


# ─── POST /firms/{firm_id}/sso — Create SSO config ──────────────────────────


@router.post("", response_model=SSOConfigResponse, status_code=201)
async def create_sso_config(
    firm_id: UUID,
    body: SSOConfigCreate,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SSOConfigResponse:
    """Create SSO configuration. Enterprise plan required. Owner only."""
    _require_owner(membership)
    config = await sso_service.create_sso_config(
        db,
        firm_id=firm_id,
        data=body.model_dump(exclude_unset=True),
        current_user=current_user,
    )
    return SSOConfigResponse.model_validate(config)


# ─── PATCH /firms/{firm_id}/sso — Update SSO config ─────────────────────────


@router.patch("", response_model=SSOConfigResponse)
async def update_sso_config(
    firm_id: UUID,
    body: SSOConfigUpdate,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SSOConfigResponse:
    """Update SSO configuration. Owner only."""
    _require_owner(membership)
    config = await sso_service.update_sso_config(
        db,
        firm_id=firm_id,
        updates=body.model_dump(exclude_unset=True),
        current_user=current_user,
    )
    return SSOConfigResponse.model_validate(config)


# ─── DELETE /firms/{firm_id}/sso — Remove SSO config ────────────────────────


@router.delete("", status_code=204)
async def delete_sso_config(
    firm_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete SSO configuration and Auth0 connection. Owner only."""
    _require_owner(membership)
    await sso_service.delete_sso_config(db, firm_id=firm_id, current_user=current_user)


# ─── POST /firms/{firm_id}/sso/enable — Enable SSO ──────────────────────────


@router.post("/enable", response_model=SSOConfigResponse)
async def enable_sso(
    firm_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SSOConfigResponse:
    """Enable SSO for the firm. Connection must be verified first."""
    _require_owner(membership)
    config = await sso_service.enable_sso(db, firm_id=firm_id, current_user=current_user)
    return SSOConfigResponse.model_validate(config)


# ─── POST /firms/{firm_id}/sso/disable — Disable SSO ────────────────────────


@router.post("/disable", response_model=SSOConfigResponse)
async def disable_sso(
    firm_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SSOConfigResponse:
    """Disable SSO (also disables enforcement)."""
    _require_owner(membership)
    config = await sso_service.disable_sso(db, firm_id=firm_id, current_user=current_user)
    return SSOConfigResponse.model_validate(config)


# ─── GET /firms/{firm_id}/sso/login-url — Get SSO login URL ─────────────────


@router.get("/login-url", response_model=SSOLoginUrlResponse)
async def get_sso_login_url(
    firm_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SSOLoginUrlResponse:
    """Get the SSO login URL. No auth required (used on login page)."""
    result = await sso_service.get_sso_login_url(db, firm_id=firm_id)
    return SSOLoginUrlResponse(**result)


# ─── GET /sso/check-enforcement — Check if email requires SSO ────────────────


@router.get("/check-enforcement")
async def check_sso_enforcement(
    email: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check if an email domain requires SSO login. No auth required.

    Called by the login page to redirect users to SSO if their domain
    requires it.
    """
    result = await sso_service.check_sso_enforcement(db, email=email)
    if result is None:
        return {"sso_required": False}
    return {"sso_required": True, **result}
