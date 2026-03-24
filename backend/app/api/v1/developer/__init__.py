"""Developer API routes — API keys and webhook management."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.security import get_current_user, require_firm_member
from app.models.enums import FirmRole
from app.models.firm_memberships import FirmMembership
from app.schemas.api_keys import APIKeyCreate, APIKeyCreatedResponse, APIKeyResponse
from app.schemas.auth import CurrentUser
from app.schemas.webhooks import (
    SupportedEventsResponse,
    WebhookCreate,
    WebhookCreatedResponse,
    WebhookDeliveryResponse,
    WebhookResponse,
    WebhookUpdate,
)
from app.services import api_key_service, webhook_service

router = APIRouter()


def _require_admin(membership: FirmMembership) -> None:
    if membership.firm_role not in (FirmRole.owner, FirmRole.admin):
        raise PermissionDeniedError(
            detail="Only firm owners and admins can manage developer settings"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# API KEYS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    firm_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> list[APIKeyResponse]:
    """List all API keys for the firm."""
    _require_admin(membership)
    keys = await api_key_service.list_api_keys(db, firm_id=firm_id)
    return [APIKeyResponse.model_validate(k) for k in keys]


@router.post("/api-keys", response_model=APIKeyCreatedResponse, status_code=201)
async def create_api_key(
    firm_id: UUID,
    body: APIKeyCreate,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIKeyCreatedResponse:
    """Create a new API key. The raw key is returned ONLY in this response."""
    _require_admin(membership)
    key_obj, raw_key = await api_key_service.create_api_key(
        db,
        firm_id=firm_id,
        name=body.name,
        description=body.description,
        scopes=body.scopes,
        rate_limit_per_minute=body.rate_limit_per_minute,
        expires_at=body.expires_at,
        current_user=current_user,
    )
    return APIKeyCreatedResponse(
        key=APIKeyResponse.model_validate(key_obj),
        raw_key=raw_key,
    )


@router.post("/api-keys/{key_id}/revoke", response_model=APIKeyResponse)
async def revoke_api_key(
    firm_id: UUID,
    key_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> APIKeyResponse:
    """Revoke an API key (soft-disable, keeps record)."""
    _require_admin(membership)
    key = await api_key_service.revoke_api_key(db, key_id=key_id, firm_id=firm_id)
    return APIKeyResponse.model_validate(key)


@router.post(
    "/api-keys/{key_id}/regenerate",
    response_model=APIKeyCreatedResponse,
)
async def regenerate_api_key(
    firm_id: UUID,
    key_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> APIKeyCreatedResponse:
    """Regenerate an API key — old key becomes invalid immediately."""
    _require_admin(membership)
    key_obj, raw_key = await api_key_service.regenerate_api_key(db, key_id=key_id, firm_id=firm_id)
    return APIKeyCreatedResponse(
        key=APIKeyResponse.model_validate(key_obj),
        raw_key=raw_key,
    )


@router.delete("/api-keys/{key_id}", status_code=204)
async def delete_api_key(
    firm_id: UUID,
    key_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Permanently delete an API key."""
    _require_admin(membership)
    await api_key_service.delete_api_key(db, key_id=key_id, firm_id=firm_id)


# ═══════════════════════════════════════════════════════════════════════════════
# WEBHOOKS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/webhooks/events", response_model=SupportedEventsResponse)
async def list_supported_events(
    _membership: FirmMembership = Depends(require_firm_member),
) -> SupportedEventsResponse:
    """List all event types available for webhook subscription."""
    return SupportedEventsResponse(events=webhook_service.get_supported_events())


@router.get("/webhooks", response_model=list[WebhookResponse])
async def list_webhooks(
    firm_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> list[WebhookResponse]:
    """List all webhooks for the firm."""
    _require_admin(membership)
    webhooks = await webhook_service.list_webhooks(db, firm_id=firm_id)
    return [WebhookResponse.model_validate(w) for w in webhooks]


@router.post("/webhooks", response_model=WebhookCreatedResponse, status_code=201)
async def create_webhook(
    firm_id: UUID,
    body: WebhookCreate,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebhookCreatedResponse:
    """Create a new webhook endpoint. Secret is returned ONLY in this response."""
    _require_admin(membership)
    webhook = await webhook_service.create_webhook(
        db,
        firm_id=firm_id,
        url=body.url,
        events=body.events,
        description=body.description,
        current_user=current_user,
    )
    return WebhookCreatedResponse.model_validate(webhook)


@router.patch("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    firm_id: UUID,
    webhook_id: UUID,
    body: WebhookUpdate,
    membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """Update a webhook's URL, events, or active status."""
    _require_admin(membership)
    webhook = await webhook_service.update_webhook(
        db,
        webhook_id=webhook_id,
        firm_id=firm_id,
        updates=body.model_dump(exclude_unset=True),
    )
    return WebhookResponse.model_validate(webhook)


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(
    firm_id: UUID,
    webhook_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a webhook and all its delivery history."""
    _require_admin(membership)
    await webhook_service.delete_webhook(db, webhook_id=webhook_id, firm_id=firm_id)


@router.post(
    "/webhooks/{webhook_id}/rotate-secret",
    response_model=WebhookCreatedResponse,
)
async def rotate_webhook_secret(
    firm_id: UUID,
    webhook_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> WebhookCreatedResponse:
    """Rotate the HMAC signing secret. New secret returned ONLY here."""
    _require_admin(membership)
    webhook = await webhook_service.rotate_secret(db, webhook_id=webhook_id, firm_id=firm_id)
    return WebhookCreatedResponse.model_validate(webhook)


@router.post(
    "/webhooks/{webhook_id}/test",
    response_model=WebhookDeliveryResponse,
)
async def test_webhook(
    firm_id: UUID,
    webhook_id: UUID,
    membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> WebhookDeliveryResponse:
    """Send a test ping to the webhook endpoint."""
    _require_admin(membership)
    delivery = await webhook_service.test_webhook(db, webhook_id=webhook_id, firm_id=firm_id)
    return WebhookDeliveryResponse.model_validate(delivery)


@router.get(
    "/webhooks/{webhook_id}/deliveries",
    response_model=list[WebhookDeliveryResponse],
)
async def list_deliveries(
    firm_id: UUID,
    webhook_id: UUID,
    limit: int = 50,
    offset: int = 0,
    membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> list[WebhookDeliveryResponse]:
    """List delivery logs for a webhook."""
    _require_admin(membership)
    deliveries = await webhook_service.list_deliveries(
        db,
        webhook_id=webhook_id,
        firm_id=firm_id,
        limit=min(limit, 100),
        offset=offset,
    )
    return [WebhookDeliveryResponse.model_validate(d) for d in deliveries]
