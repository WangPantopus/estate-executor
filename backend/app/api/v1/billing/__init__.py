"""Stripe billing API routes — subscription management and webhooks."""

from __future__ import annotations

import logging
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.core.security import get_current_user, require_firm_member
from app.models.enums import FirmRole
from app.models.firm_memberships import FirmMembership
from app.schemas.auth import CurrentUser
from app.schemas.billing import (
    BillingOverviewResponse,
    CheckoutSessionResponse,
    CreateCheckoutRequest,
    CreatePortalSessionRequest,
    InvoiceListResponse,
    InvoiceResponse,
    PortalSessionResponse,
    SubscriptionResponse,
    UsageResponse,
)
from app.services import billing_service

logger = logging.getLogger(__name__)

router = APIRouter()
webhook_router = APIRouter()


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _require_owner_or_admin(membership: FirmMembership) -> None:
    if membership.firm_role not in (FirmRole.owner, FirmRole.admin):
        from app.core.exceptions import PermissionDeniedError

        raise PermissionDeniedError(detail="Only owners and admins can manage billing")


# ─── GET /firms/{firm_id}/billing — Billing overview ─────────────────────────


@router.get("", response_model=BillingOverviewResponse)
async def get_billing_overview(
    firm_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> BillingOverviewResponse:
    """Get billing overview: subscription info, tier limits, and usage."""
    sub = await billing_service.get_or_create_subscription(db, firm_id=firm_id)
    sub = await billing_service.sync_usage_counts(db, firm_id=firm_id)

    tier_str = sub.tier.value if hasattr(sub.tier, "value") else sub.tier
    limits = billing_service.get_tier_limits(tier_str)

    return BillingOverviewResponse(
        subscription=SubscriptionResponse.model_validate(sub),
        tier_limits=billing_service.get_all_tier_limits(),
        usage=UsageResponse(
            matter_count=sub.matter_count,
            matter_limit=limits.max_matters,
            user_count=sub.user_count,
            user_limit=limits.max_users,
        ),
    )


# ─── POST /firms/{firm_id}/billing/checkout — Create checkout session ────────


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout(
    firm_id: UUID,
    body: CreateCheckoutRequest,
    membership: FirmMembership = Depends(require_firm_member),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutSessionResponse:
    """Create a Stripe Checkout session for subscription signup/upgrade."""
    _require_owner_or_admin(membership)

    result = await billing_service.create_checkout_session(
        db,
        firm_id=firm_id,
        tier=body.tier,
        billing_interval=body.billing_interval,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        current_user=current_user,
    )
    return CheckoutSessionResponse(**result)


# ─── POST /firms/{firm_id}/billing/portal — Stripe Customer Portal ───────────


@router.post("/portal", response_model=PortalSessionResponse)
async def create_portal_session(
    firm_id: UUID,
    body: CreatePortalSessionRequest | None = None,
    membership: FirmMembership = Depends(require_firm_member),
    _current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalSessionResponse:
    """Create a Stripe Customer Portal session for managing subscription."""
    _require_owner_or_admin(membership)

    result = await billing_service.create_portal_session(
        db,
        firm_id=firm_id,
        return_url=body.return_url if body else None,
    )
    return PortalSessionResponse(**result)


# ─── GET /firms/{firm_id}/billing/invoices — Invoice history ─────────────────


@router.get("/invoices", response_model=InvoiceListResponse)
async def get_invoices(
    firm_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> InvoiceListResponse:
    """Get recent invoices from Stripe."""
    result = await billing_service.get_invoices(db, firm_id=firm_id)
    return InvoiceListResponse(
        invoices=[InvoiceResponse(**inv) for inv in result["invoices"]],
        has_more=result["has_more"],
    )


# ─── GET /firms/{firm_id}/billing/usage — Usage stats ────────────────────────


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    firm_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    db: AsyncSession = Depends(get_db),
) -> UsageResponse:
    """Get current usage counts vs tier limits."""
    sub = await billing_service.sync_usage_counts(db, firm_id=firm_id)
    tier_str = sub.tier.value if hasattr(sub.tier, "value") else sub.tier
    limits = billing_service.get_tier_limits(tier_str)

    return UsageResponse(
        matter_count=sub.matter_count,
        matter_limit=limits.max_matters,
        user_count=sub.user_count,
        user_limit=limits.max_users,
    )


# ─── POST /webhooks/stripe — Stripe webhook handler ─────────────────────────


@webhook_router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Handle Stripe webhook events.

    Verifies the webhook signature, then dispatches to the billing service.
    """
    body = await request.body()

    if not stripe_signature:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing Stripe-Signature header"},
        )

    try:
        event = stripe.Webhook.construct_event(
            payload=body,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
        )
    except ValueError:
        logger.warning("stripe_webhook_invalid_payload")
        return JSONResponse(status_code=400, content={"error": "Invalid payload"})
    except stripe.SignatureVerificationError:
        logger.warning("stripe_webhook_invalid_signature")
        return JSONResponse(status_code=400, content={"error": "Invalid signature"})

    try:
        await billing_service.handle_webhook_event(db, event=event)
    except Exception:
        logger.exception("stripe_webhook_handler_error")
        # Return 200 to prevent Stripe from retrying for app errors
        # The error is logged for investigation

    return JSONResponse(status_code=200, content={"received": True})
