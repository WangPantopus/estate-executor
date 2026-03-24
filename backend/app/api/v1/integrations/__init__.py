"""Integration management API routes — OAuth, sync, webhooks, settings."""

from __future__ import annotations

import hashlib
import hmac
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.security import get_current_user, require_firm_member
from app.models.enums import FirmRole
from app.models.firm_memberships import FirmMembership
from app.schemas.auth import CurrentUser
from app.schemas.integrations import (
    ClioSettingsUpdate,
    DisconnectResponse,
    IntegrationConnectionResponse,
    IntegrationListResponse,
    OAuthInitResponse,
    SyncRequest,
    SyncResultResponse,
)
from app.services import clio_sync_service

logger = logging.getLogger(__name__)

router = APIRouter()
webhook_router = APIRouter()


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _require_admin(membership: FirmMembership) -> None:
    if membership.firm_role not in (FirmRole.owner, FirmRole.admin):
        raise PermissionDeniedError(detail="Only owners and admins can manage integrations")


# ─── GET /firms/{firm_id}/integrations — List connections ────────────────────


@router.get("", response_model=IntegrationListResponse)
async def list_integrations(
    firm_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> IntegrationListResponse:
    """List all integration connections for a firm."""
    from sqlalchemy import select

    from app.models.integration_connections import IntegrationConnection

    result = await db.execute(
        select(IntegrationConnection).where(IntegrationConnection.firm_id == firm_id)
    )
    connections = list(result.scalars().all())
    return IntegrationListResponse(
        connections=[IntegrationConnectionResponse.model_validate(c) for c in connections]
    )


# ─── POST /firms/{firm_id}/integrations/clio/connect — Start OAuth ──────────


@router.post("/clio/connect", response_model=OAuthInitResponse)
async def clio_connect(
    firm_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OAuthInitResponse:
    """Initiate the Clio OAuth2 connection flow."""
    _require_admin(membership)
    result = await clio_sync_service.initiate_oauth(db, firm_id=firm_id, current_user=current_user)
    return OAuthInitResponse(**result)


# ─── GET /integrations/clio/callback — OAuth callback ────────────────────────


@router.get("/clio/callback")
async def clio_callback(
    code: str = Query(...),
    state: str = Query(...),
    firm_id: str = Query("", alias="firm_id"),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle Clio OAuth2 callback. Redirects to frontend settings page."""
    # The firm_id is encoded in the state; we look it up from pending connections
    from sqlalchemy import select

    from app.models.integration_connections import IntegrationConnection

    result = await db.execute(
        select(IntegrationConnection).where(
            IntegrationConnection.provider == "clio",
        )
    )
    connections = list(result.scalars().all())

    matched_conn = None
    for conn in connections:
        if conn.settings.get("oauth_state") == state:
            matched_conn = conn
            break

    if matched_conn is None:
        frontend_url = settings.frontend_url
        return RedirectResponse(url=f"{frontend_url}/settings?tab=integrations&error=invalid_state")

    try:
        await clio_sync_service.complete_oauth(
            db, firm_id=matched_conn.firm_id, code=code, state=state
        )
        frontend_url = settings.frontend_url
        return RedirectResponse(url=f"{frontend_url}/settings?tab=integrations&clio=connected")
    except Exception:
        logger.error("clio_oauth_callback_failed", exc_info=True)
        frontend_url = settings.frontend_url
        return RedirectResponse(
            url=f"{frontend_url}/settings?tab=integrations&error=connection_failed"
        )


# ─── GET /firms/{firm_id}/integrations/clio — Get Clio connection ────────────


@router.get("/clio", response_model=IntegrationConnectionResponse | None)
async def get_clio_connection(
    firm_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> IntegrationConnectionResponse | None:
    """Get the Clio integration connection status."""
    conn = await clio_sync_service.get_connection(db, firm_id=firm_id, provider="clio")
    if conn is None:
        return None
    return IntegrationConnectionResponse.model_validate(conn)


# ─── POST /firms/{firm_id}/integrations/clio/disconnect — Disconnect ─────────


@router.post("/clio/disconnect", response_model=DisconnectResponse)
async def clio_disconnect(
    firm_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DisconnectResponse:
    """Disconnect the Clio integration."""
    _require_admin(membership)
    await clio_sync_service.disconnect(db, firm_id=firm_id, current_user=current_user)
    return DisconnectResponse(provider="clio")


# ─── PATCH /firms/{firm_id}/integrations/clio/settings — Update settings ─────


@router.patch("/clio/settings", response_model=IntegrationConnectionResponse)
async def update_clio_settings(
    firm_id: UUID,
    body: ClioSettingsUpdate,
    membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> IntegrationConnectionResponse:
    """Update Clio integration settings."""
    _require_admin(membership)
    conn = await clio_sync_service.update_settings(
        db, firm_id=firm_id, updates=body.model_dump(exclude_unset=True)
    )
    return IntegrationConnectionResponse.model_validate(conn)


# ─── POST /firms/{firm_id}/integrations/clio/sync — Trigger sync ─────────────


@router.post("/clio/sync", response_model=SyncResultResponse)
async def clio_sync(
    firm_id: UUID,
    body: SyncRequest,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncResultResponse:
    """Trigger a manual sync with Clio for a specific resource."""
    _require_admin(membership)

    if body.resource == "matters":
        result = await clio_sync_service.sync_matters(
            db, firm_id=firm_id, current_user=current_user, direction=body.direction
        )
    elif body.resource == "time_entries":
        result = await clio_sync_service.sync_time_entries(
            db,
            firm_id=firm_id,
            current_user=current_user,
            matter_id=body.matter_id,
        )
    elif body.resource == "contacts":
        result = await clio_sync_service.sync_contacts(
            db, firm_id=firm_id, current_user=current_user, direction=body.direction
        )
    else:
        from app.core.exceptions import ValidationError

        raise ValidationError(detail=f"Unknown resource: {body.resource}")

    return SyncResultResponse(**result)


# ─── POST /webhooks/clio — Clio webhook handler ─────────────────────────────


@webhook_router.post("/clio")
async def clio_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Handle inbound Clio webhook events."""
    body = await request.body()

    # Verify webhook signature — reject if secret not configured
    if not settings.clio_webhook_secret:
        logger.error("clio_webhook_secret_not_configured")
        return JSONResponse(
            status_code=500, content={"error": "Webhook secret not configured"}
        )

    signature = request.headers.get("X-Clio-Signature", "")
    expected = hmac.new(
        settings.clio_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        logger.warning("clio_webhook_invalid_signature")
        return JSONResponse(status_code=401, content={"error": "Invalid signature"})

    try:
        import json

        payload = json.loads(body)
        await clio_sync_service.handle_clio_webhook(db, payload=payload)
    except Exception:
        logger.exception("clio_webhook_handler_error")

    return JSONResponse(status_code=200, content={"received": True})
