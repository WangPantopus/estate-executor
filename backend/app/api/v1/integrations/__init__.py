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
from app.schemas.docusign import (
    SendForSignatureRequest,
    SignatureRequestListResponse,
    SignatureRequestResponse,
    VoidEnvelopeRequest,
)
from app.schemas.integrations import (
    ClioSettingsUpdate,
    DisconnectResponse,
    IntegrationConnectionResponse,
    IntegrationListResponse,
    OAuthInitResponse,
    SyncRequest,
    SyncResultResponse,
)
from app.services import clio_sync_service, docusign_service, quickbooks_sync_service

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
    firm_id: UUID,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle Clio OAuth2 callback. Redirects to frontend settings page."""
    # The firm_id comes from the path; we look it up from pending connections
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
        return JSONResponse(status_code=500, content={"error": "Webhook secret not configured"})

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


# ═══════════════════════════════════════════════════════════════════════════════
# DocuSign Integration
# ═══════════════════════════════════════════════════════════════════════════════


# ─── POST /firms/{firm_id}/integrations/docusign/connect ─────────────────────


@router.post("/docusign/connect", response_model=OAuthInitResponse)
async def docusign_connect(
    firm_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OAuthInitResponse:
    """Initiate DocuSign OAuth2 connection."""
    _require_admin(membership)
    result = await docusign_service.initiate_oauth(db, firm_id=firm_id, current_user=current_user)
    return OAuthInitResponse(**result)


# ─── GET /integrations/docusign/callback ─────────────────────────────────────


@router.get("/docusign/callback")
async def docusign_callback(
    firm_id: UUID,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle DocuSign OAuth2 callback."""
    from sqlalchemy import select as sa_select

    from app.models.integration_connections import IntegrationConnection as IntConn

    result = await db.execute(sa_select(IntConn).where(IntConn.provider == "docusign"))
    connections = list(result.scalars().all())
    matched = None
    for conn in connections:
        if conn.settings.get("oauth_state") == state:
            matched = conn
            break

    frontend_url = settings.frontend_url
    if matched is None:
        return RedirectResponse(url=f"{frontend_url}/settings?tab=integrations&error=invalid_state")

    try:
        await docusign_service.complete_oauth(db, firm_id=matched.firm_id, code=code, state=state)
        return RedirectResponse(url=f"{frontend_url}/settings?tab=integrations&docusign=connected")
    except Exception:
        logger.error("docusign_oauth_callback_failed", exc_info=True)
        return RedirectResponse(
            url=f"{frontend_url}/settings?tab=integrations&error=connection_failed"
        )


# ─── GET /firms/{firm_id}/integrations/docusign ──────────────────────────────


@router.get("/docusign", response_model=IntegrationConnectionResponse | None)
async def get_docusign_connection(
    firm_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> IntegrationConnectionResponse | None:
    """Get DocuSign connection status."""
    conn = await docusign_service.get_connection(db, firm_id=firm_id)
    if conn is None:
        return None
    return IntegrationConnectionResponse.model_validate(conn)


# ─── POST /firms/{firm_id}/integrations/docusign/disconnect ──────────────────


@router.post("/docusign/disconnect", response_model=DisconnectResponse)
async def docusign_disconnect(
    firm_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DisconnectResponse:
    """Disconnect DocuSign."""
    _require_admin(membership)
    await docusign_service.disconnect(db, firm_id=firm_id, current_user=current_user)
    return DisconnectResponse(provider="docusign")


# ─── Signature request endpoints (scoped to matter) ─────────────────────────


@router.post(
    "/docusign/matters/{matter_id}/send",
    response_model=SignatureRequestResponse,
    status_code=201,
)
async def send_for_signature(
    firm_id: UUID,
    matter_id: UUID,
    body: SendForSignatureRequest,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SignatureRequestResponse:
    """Send a document for e-signature via DocuSign."""
    from app.core.security import require_stakeholder

    stakeholder = await require_stakeholder(
        matter_id,
        current_user=current_user,
        db=db,
    )

    sig_req = await docusign_service.send_for_signature(
        db,
        firm_id=firm_id,
        matter_id=matter_id,
        document_id=body.document_id,
        request_type=body.request_type,
        subject=body.subject,
        message=body.message,
        signers=[s.model_dump() for s in body.signers],
        stakeholder_id=stakeholder.id,
        current_user=current_user,
    )
    return SignatureRequestResponse.model_validate(sig_req)


@router.get(
    "/docusign/matters/{matter_id}/requests",
    response_model=SignatureRequestListResponse,
)
async def list_signature_requests(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> SignatureRequestListResponse:
    """List signature requests for a matter."""
    items, total = await docusign_service.list_signature_requests(db, matter_id=matter_id)
    return SignatureRequestListResponse(
        data=[SignatureRequestResponse.model_validate(r) for r in items],
        total=total,
    )


@router.get(
    "/docusign/matters/{matter_id}/requests/{request_id}",
    response_model=SignatureRequestResponse,
)
async def get_signature_request(
    firm_id: UUID,
    matter_id: UUID,
    request_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> SignatureRequestResponse:
    """Get a specific signature request with signer statuses."""
    sig_req = await docusign_service.get_signature_request(
        db, request_id=request_id, matter_id=matter_id
    )
    return SignatureRequestResponse.model_validate(sig_req)


@router.post(
    "/docusign/matters/{matter_id}/requests/{request_id}/refresh",
    response_model=SignatureRequestResponse,
)
async def refresh_signature_status(
    firm_id: UUID,
    matter_id: UUID,
    request_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> SignatureRequestResponse:
    """Poll DocuSign for latest envelope status."""
    sig_req = await docusign_service.refresh_envelope_status(
        db,
        firm_id=firm_id,
        request_id=request_id,
        matter_id=matter_id,
    )
    return SignatureRequestResponse.model_validate(sig_req)


@router.post(
    "/docusign/matters/{matter_id}/requests/{request_id}/void",
    response_model=SignatureRequestResponse,
)
async def void_signature_request(
    firm_id: UUID,
    matter_id: UUID,
    request_id: UUID,
    body: VoidEnvelopeRequest,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SignatureRequestResponse:
    """Void (cancel) a signature request."""
    _require_admin(membership)
    sig_req = await docusign_service.void_envelope(
        db,
        firm_id=firm_id,
        request_id=request_id,
        matter_id=matter_id,
        reason=body.reason,
        current_user=current_user,
    )
    return SignatureRequestResponse.model_validate(sig_req)


# ─── POST /webhooks/docusign — DocuSign Connect webhook ─────────────────────


@webhook_router.post("/docusign")
async def docusign_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Handle DocuSign Connect webhook notifications."""
    body = await request.body()

    # Verify HMAC signature if configured
    if not settings.docusign_webhook_secret:
        logger.error("docusign_webhook_secret_not_configured")
        return JSONResponse(
            status_code=500,
            content={"error": "Webhook secret not configured"},
        )

    import json

    # DocuSign uses multiple signature headers depending on config
    ds_signature = request.headers.get("X-DocuSign-Signature-1", "")
    if not ds_signature:
        logger.warning("docusign_webhook_missing_signature")
        return JSONResponse(
            status_code=401,
            content={"error": "Missing signature header"},
        )

    expected = hmac.new(
        settings.docusign_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(ds_signature, expected):
        logger.warning("docusign_webhook_invalid_signature")
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid signature"},
        )

    try:
        payload = json.loads(body)
        await docusign_service.handle_docusign_webhook(db, payload=payload)
    except Exception:
        logger.exception("docusign_webhook_handler_error")

    return JSONResponse(status_code=200, content={"received": True})


# ═══════════════════════════════════════════════════════════════════════════════
# QuickBooks Online Integration
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/quickbooks/connect", response_model=OAuthInitResponse)
async def quickbooks_connect(
    firm_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OAuthInitResponse:
    """Initiate QuickBooks Online OAuth2 connection."""
    _require_admin(membership)
    result = await quickbooks_sync_service.initiate_oauth(
        db, firm_id=firm_id, current_user=current_user
    )
    return OAuthInitResponse(**result)


@router.get("/quickbooks/callback")
async def quickbooks_callback(
    firm_id: UUID,
    code: str = Query(...),
    state: str = Query(...),
    realm_id: str = Query(..., alias="realmId"),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle QuickBooks OAuth2 callback (includes realmId)."""
    from sqlalchemy import select as sa_select

    from app.models.integration_connections import IntegrationConnection as IntConn

    result = await db.execute(sa_select(IntConn).where(IntConn.provider == "quickbooks"))
    connections = list(result.scalars().all())
    matched = None
    for conn in connections:
        if conn.settings.get("oauth_state") == state:
            matched = conn
            break

    frontend_url = settings.frontend_url
    if matched is None:
        return RedirectResponse(url=f"{frontend_url}/settings?tab=integrations&error=invalid_state")

    try:
        await quickbooks_sync_service.complete_oauth(
            db,
            firm_id=matched.firm_id,
            code=code,
            state=state,
            realm_id=realm_id,
        )
        return RedirectResponse(
            url=f"{frontend_url}/settings?tab=integrations&quickbooks=connected"
        )
    except Exception:
        logger.error("qbo_oauth_callback_failed", exc_info=True)
        return RedirectResponse(
            url=f"{frontend_url}/settings?tab=integrations&error=connection_failed"
        )


@router.get("/quickbooks", response_model=IntegrationConnectionResponse | None)
async def get_quickbooks_connection(
    firm_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> IntegrationConnectionResponse | None:
    conn = await quickbooks_sync_service.get_connection(db, firm_id=firm_id)
    if conn is None:
        return None
    return IntegrationConnectionResponse.model_validate(conn)


@router.post("/quickbooks/disconnect", response_model=DisconnectResponse)
async def quickbooks_disconnect(
    firm_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DisconnectResponse:
    _require_admin(membership)
    await quickbooks_sync_service.disconnect(db, firm_id=firm_id, current_user=current_user)
    return DisconnectResponse(provider="quickbooks")


@router.post("/quickbooks/sync", response_model=SyncResultResponse)
async def quickbooks_sync(
    firm_id: UUID,
    body: SyncRequest,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncResultResponse:
    """Trigger a QuickBooks sync (distributions, transactions, or balances)."""
    _require_admin(membership)

    from app.core.exceptions import ValidationError

    if body.resource == "distributions":
        sync_result = await quickbooks_sync_service.push_distributions(
            db,
            firm_id=firm_id,
            current_user=current_user,
            matter_id=body.matter_id,
        )
    elif body.resource == "transactions":
        sync_result = await quickbooks_sync_service.push_transactions(
            db,
            firm_id=firm_id,
            current_user=current_user,
            matter_id=body.matter_id,
        )
    elif body.resource == "account_balances":
        sync_result = await quickbooks_sync_service.pull_account_balances(
            db, firm_id=firm_id, current_user=current_user
        )
    else:
        raise ValidationError(detail=f"Unknown resource: {body.resource}")

    return SyncResultResponse(**sync_result)
