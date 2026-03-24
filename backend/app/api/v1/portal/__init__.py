"""Beneficiary Portal API routes — read-only endpoints for beneficiaries."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.security import get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.portal import (
    PortalBeneficiaryMattersResponse,
    PortalDocumentItem,
    PortalDocumentsResponse,
    PortalMatterBrief,
    PortalMessageCreate,
    PortalMessageItem,
    PortalMessagesResponse,
    PortalOverviewResponse,
)
from app.services import portal_service

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /portal/matters — list matters where user is a beneficiary
# ---------------------------------------------------------------------------


@router.get("/matters", response_model=PortalBeneficiaryMattersResponse)
async def list_beneficiary_matters(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalBeneficiaryMattersResponse:
    """List all matters where the current user is a beneficiary."""
    matters = await portal_service.list_beneficiary_matters(db, current_user=current_user)
    return PortalBeneficiaryMattersResponse(matters=[PortalMatterBrief(**m) for m in matters])


# ---------------------------------------------------------------------------
# GET /portal/matters/{matter_id}/overview
# ---------------------------------------------------------------------------


@router.get("/matters/{matter_id}/overview", response_model=PortalOverviewResponse)
async def get_portal_overview(
    matter_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalOverviewResponse:
    """Get the portal overview for a specific matter."""
    data = await portal_service.get_portal_overview(
        db, matter_id=matter_id, current_user=current_user
    )
    return PortalOverviewResponse(**data)


# ---------------------------------------------------------------------------
# GET /portal/matters/{matter_id}/documents
# ---------------------------------------------------------------------------


@router.get("/matters/{matter_id}/documents", response_model=PortalDocumentsResponse)
async def get_portal_documents(
    matter_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalDocumentsResponse:
    """Get documents shared with the beneficiary."""
    data = await portal_service.get_portal_documents(
        db, matter_id=matter_id, current_user=current_user
    )
    return PortalDocumentsResponse(
        documents=[PortalDocumentItem(**d) for d in data["documents"]],
        total=data["total"],
    )


# ---------------------------------------------------------------------------
# GET /portal/matters/{matter_id}/messages
# ---------------------------------------------------------------------------


@router.get("/matters/{matter_id}/messages", response_model=PortalMessagesResponse)
async def get_portal_messages(
    matter_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalMessagesResponse:
    """Get communications visible to the beneficiary."""
    data = await portal_service.get_portal_messages(
        db, matter_id=matter_id, current_user=current_user
    )
    return PortalMessagesResponse(
        messages=[PortalMessageItem(**m) for m in data["messages"]],
        total=data["total"],
    )


# ---------------------------------------------------------------------------
# POST /portal/matters/{matter_id}/messages — send message
# ---------------------------------------------------------------------------


@router.post("/matters/{matter_id}/messages", response_model=PortalMessageItem, status_code=201)
async def post_portal_message(
    matter_id: UUID,
    body: PortalMessageCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalMessageItem:
    """Post a message from the beneficiary."""
    data = await portal_service.post_beneficiary_message(
        db,
        matter_id=matter_id,
        current_user=current_user,
        subject=body.subject,
        body=body.body,
    )
    return PortalMessageItem(**data)


# ---------------------------------------------------------------------------
# POST /portal/matters/{matter_id}/messages/{comm_id}/acknowledge
# ---------------------------------------------------------------------------


@router.post(
    "/matters/{matter_id}/messages/{comm_id}/acknowledge",
    response_model=PortalMessageItem,
)
async def acknowledge_notice(
    matter_id: UUID,
    comm_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalMessageItem:
    """Acknowledge a distribution notice."""
    data = await portal_service.acknowledge_distribution_notice(
        db,
        matter_id=matter_id,
        communication_id=comm_id,
        current_user=current_user,
    )
    return PortalMessageItem(**data)


# ---------------------------------------------------------------------------
# GET /portal/branding/{firm_slug} — Public branding for portal rendering
# ---------------------------------------------------------------------------


@router.get("/branding/{firm_slug}")
async def get_portal_branding(
    firm_slug: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get branding config for portal display. No auth required.

    Only exposes visual branding fields, not internal settings.
    """
    from sqlalchemy import select

    from app.models.firms import Firm
    from app.services.branding_service import get_branding

    result = await db.execute(select(Firm).where(Firm.slug == firm_slug))
    firm = result.scalar_one_or_none()
    if firm is None:
        return {
            "firm_name": "Estate Executor",
            "logo_url": None,
            "primary_color": "#1a2332",
            "accent_color": "#3b82f6",
            "powered_by_visible": True,
        }

    branding = await get_branding(db, firm_id=firm.id)
    return {
        "firm_name": branding.get("firm_display_name") or firm.name,
        "logo_url": branding.get("logo_url"),
        "logo_dark_url": branding.get("logo_dark_url"),
        "favicon_url": branding.get("favicon_url"),
        "primary_color": branding.get("primary_color"),
        "accent_color": branding.get("accent_color"),
        "portal_welcome_text": branding.get("portal_welcome_text"),
        "powered_by_visible": branding.get("powered_by_visible", True),
    }
