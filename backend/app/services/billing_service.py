"""Stripe billing service — subscription lifecycle, limit enforcement, webhooks."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import stripe
from sqlalchemy import func, select

from app.core.config import settings
from app.core.events import event_logger
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.enums import (
    ActorType,
    BillingInterval,
    MatterStatus,
    SubscriptionStatus,
    SubscriptionTier,
)
from app.models.firm_memberships import FirmMembership
from app.models.firms import Firm
from app.models.matters import Matter
from app.models.subscriptions import Subscription
from app.schemas.billing import TierLimits

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

# ─── Stripe client config ────────────────────────────────────────────────────

stripe.api_key = settings.stripe_secret_key

# ─── Tier definitions ────────────────────────────────────────────────────────

TIER_CONFIG: dict[str, TierLimits] = {
    "starter": TierLimits(
        max_matters=10,
        max_users=2,
        monthly_price_cents=4900,
        annual_price_cents=47000,  # ~$392/yr — 2 months free
    ),
    "professional": TierLimits(
        max_matters=50,
        max_users=5,
        monthly_price_cents=14900,
        annual_price_cents=143000,  # ~$1192/yr — 2 months free
    ),
    "growth": TierLimits(
        max_matters=200,
        max_users=15,
        monthly_price_cents=34900,
        annual_price_cents=335000,  # ~$2792/yr — 2 months free
    ),
    "enterprise": TierLimits(
        max_matters=999999,
        max_users=999999,
        monthly_price_cents=0,
        annual_price_cents=0,
    ),
}

# Grace period days after payment failure before restricting access
GRACE_PERIOD_DAYS = 7

# ─── Tier helpers ────────────────────────────────────────────────────────────


def get_tier_limits(tier: str) -> TierLimits:
    """Return limits for a tier, defaulting to starter."""
    return TIER_CONFIG.get(tier, TIER_CONFIG["starter"])


def get_all_tier_limits() -> dict[str, TierLimits]:
    """Return all tier configurations."""
    return TIER_CONFIG.copy()


# ─── Subscription CRUD ──────────────────────────────────────────────────────


async def get_or_create_subscription(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
) -> Subscription:
    """Get existing subscription or create a default starter one."""
    result = await db.execute(select(Subscription).where(Subscription.firm_id == firm_id))
    sub = result.scalar_one_or_none()
    if sub is not None:
        return sub

    # Auto-create a starter subscription
    sub = Subscription(
        firm_id=firm_id,
        tier=SubscriptionTier.starter,
        status=SubscriptionStatus.active,
        billing_interval=BillingInterval.month,
    )
    db.add(sub)
    await db.flush()
    return sub


async def get_subscription(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
) -> Subscription | None:
    """Get subscription for a firm."""
    result = await db.execute(select(Subscription).where(Subscription.firm_id == firm_id))
    return result.scalar_one_or_none()


# ─── Usage counting ─────────────────────────────────────────────────────────


async def count_active_matters(
    db: AsyncSession,
    firm_id: uuid.UUID,
) -> int:
    """Count active (non-archived, non-closed) matters for a firm."""
    result = await db.execute(
        select(func.count())
        .select_from(Matter)
        .where(
            Matter.firm_id == firm_id,
            Matter.status.in_([MatterStatus.active, MatterStatus.on_hold]),
        )
    )
    return result.scalar_one()


async def count_firm_users(
    db: AsyncSession,
    firm_id: uuid.UUID,
) -> int:
    """Count firm members (seats)."""
    result = await db.execute(
        select(func.count()).select_from(FirmMembership).where(FirmMembership.firm_id == firm_id)
    )
    return result.scalar_one()


async def sync_usage_counts(
    db: AsyncSession,
    firm_id: uuid.UUID,
) -> Subscription:
    """Refresh denormalized usage counts on the subscription row."""
    sub = await get_or_create_subscription(db, firm_id=firm_id)
    sub.matter_count = await count_active_matters(db, firm_id)
    sub.user_count = await count_firm_users(db, firm_id)
    await db.flush()
    return sub


# ─── Limit enforcement ──────────────────────────────────────────────────────


async def check_matter_limit(
    db: AsyncSession,
    firm_id: uuid.UUID,
) -> None:
    """Raise if firm has hit its matter limit.

    Called before creating a new matter.
    """
    sub = await get_or_create_subscription(db, firm_id=firm_id)
    _check_access_allowed(sub)

    current = await count_active_matters(db, firm_id)
    limits = get_tier_limits(sub.tier.value if hasattr(sub.tier, "value") else sub.tier)

    if current >= limits.max_matters:
        raise ConflictError(
            detail=(
                f"Matter limit reached ({current}/{limits.max_matters}). "
                f"Upgrade to a higher plan to create more matters."
            )
        )


async def check_user_limit(
    db: AsyncSession,
    firm_id: uuid.UUID,
) -> None:
    """Raise if firm has hit its user/seat limit.

    Called before inviting a new firm member.
    """
    sub = await get_or_create_subscription(db, firm_id=firm_id)
    _check_access_allowed(sub)

    current = await count_firm_users(db, firm_id)
    limits = get_tier_limits(sub.tier.value if hasattr(sub.tier, "value") else sub.tier)

    if current >= limits.max_users:
        raise ConflictError(
            detail=(
                f"User limit reached ({current}/{limits.max_users}). "
                f"Upgrade to a higher plan to add more team members."
            )
        )


def _check_access_allowed(sub: Subscription) -> None:
    """Raise if the subscription is in a restricted state (dunning expired)."""
    status = sub.status.value if hasattr(sub.status, "value") else sub.status

    if status in ("canceled", "unpaid"):
        raise ConflictError(
            detail="Your subscription is inactive. Please update your billing to continue."
        )

    if status == "past_due" and sub.grace_period_end and datetime.now(UTC) > sub.grace_period_end:
        raise ConflictError(
            detail=(
                "Your subscription payment is overdue and the grace period has expired. "
                "Please update your payment method to restore access."
            )
        )


# ─── Stripe: Customer & Checkout ─────────────────────────────────────────────


async def ensure_stripe_customer(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
) -> str:
    """Get or create a Stripe customer for the firm."""
    result = await db.execute(select(Firm).where(Firm.id == firm_id))
    firm = result.scalar_one_or_none()
    if firm is None:
        raise NotFoundError(detail="Firm not found")

    if firm.stripe_customer_id:
        return firm.stripe_customer_id

    try:
        customer = stripe.Customer.create(
            name=firm.name,
            metadata={"firm_id": str(firm_id), "firm_slug": firm.slug},
        )
    except stripe.StripeError as e:
        logger.error("stripe_customer_create_failed", exc_info=True)
        raise ValidationError(detail=f"Failed to create billing account: {e}") from e

    firm.stripe_customer_id = customer.id
    await db.flush()
    return customer.id


async def create_checkout_session(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    tier: str,
    billing_interval: str = "month",
    success_url: str | None = None,
    cancel_url: str | None = None,
    current_user: CurrentUser,
) -> dict[str, str]:
    """Create a Stripe Checkout session for new subscription or upgrade."""
    if tier not in TIER_CONFIG or tier == "enterprise":
        raise ValidationError(detail=f"Invalid tier: {tier}")
    if billing_interval not in ("month", "year"):
        raise ValidationError(detail="billing_interval must be 'month' or 'year'")

    customer_id = await ensure_stripe_customer(db, firm_id=firm_id)
    limits = TIER_CONFIG[tier]

    # Determine price — use configured Stripe price IDs if available,
    # otherwise create a price on the fly (for development)
    price_id = (
        limits.stripe_annual_price_id
        if billing_interval == "year"
        else limits.stripe_monthly_price_id
    )

    try:
        if not price_id:
            # Development fallback: create ad-hoc price
            price_cents = (
                limits.annual_price_cents
                if billing_interval == "year"
                else limits.monthly_price_cents
            )
            price = stripe.Price.create(
                unit_amount=price_cents,
                currency="usd",
                recurring={"interval": billing_interval},  # type: ignore[typeddict-item]
                product_data={
                    "name": f"Estate Executor OS — {tier.title()}",
                },
            )
            price_id = price.id

        frontend_url = settings.frontend_url
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url or f"{frontend_url}/settings?billing=success",
            cancel_url=cancel_url or f"{frontend_url}/settings?billing=cancel",
            metadata={
                "firm_id": str(firm_id),
                "tier": tier,
                "billing_interval": billing_interval,
            },
            subscription_data={
                "metadata": {
                    "firm_id": str(firm_id),
                    "tier": tier,
                },
            },
            allow_promotion_codes=True,
        )
    except stripe.StripeError as e:
        logger.error("stripe_checkout_create_failed", exc_info=True)
        raise ValidationError(detail=f"Failed to create checkout session: {e}") from e

    await event_logger.log(
        db,
        matter_id=firm_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="subscription",
        entity_id=firm_id,
        action="checkout_initiated",
        metadata={"tier": tier, "billing_interval": billing_interval},
    )

    return {"checkout_url": session.url or "", "session_id": session.id}


async def create_portal_session(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    return_url: str | None = None,
) -> dict[str, str]:
    """Create a Stripe Customer Portal session for managing billing."""
    customer_id = await ensure_stripe_customer(db, firm_id=firm_id)
    frontend_url = settings.frontend_url

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url or f"{frontend_url}/settings?tab=billing",
        )
    except stripe.StripeError as e:
        logger.error("stripe_portal_create_failed", exc_info=True)
        raise ValidationError(detail=f"Failed to create billing portal session: {e}") from e

    return {"portal_url": session.url}


async def get_invoices(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    limit: int = 10,
) -> dict[str, Any]:
    """Fetch recent invoices from Stripe for the firm."""
    result = await db.execute(select(Firm).where(Firm.id == firm_id))
    firm = result.scalar_one_or_none()
    if firm is None or not firm.stripe_customer_id:
        return {"invoices": [], "has_more": False}

    try:
        invoices = stripe.Invoice.list(
            customer=firm.stripe_customer_id,
            limit=limit,
        )
    except stripe.StripeError:
        logger.warning("stripe_invoice_list_failed", exc_info=True)
        return {"invoices": [], "has_more": False}

    items = []
    for inv in invoices.data:
        items.append(
            {
                "id": inv.id,
                "amount_due": inv.amount_due,
                "amount_paid": inv.amount_paid,
                "currency": inv.currency,
                "status": inv.status,
                "invoice_url": inv.hosted_invoice_url,
                "invoice_pdf": inv.invoice_pdf,
                "period_start": (
                    datetime.fromtimestamp(inv.period_start, tz=UTC) if inv.period_start else None
                ),
                "period_end": (
                    datetime.fromtimestamp(inv.period_end, tz=UTC) if inv.period_end else None
                ),
                "created": (datetime.fromtimestamp(inv.created, tz=UTC) if inv.created else None),
            }
        )

    return {"invoices": items, "has_more": invoices.has_more}


# ─── Webhook handling ────────────────────────────────────────────────────────


async def handle_webhook_event(
    db: AsyncSession,
    *,
    event: stripe.Event,
) -> None:
    """Process a Stripe webhook event. Dispatches to specific handlers."""
    event_type = event.type
    data_obj = event.data.object

    handler = _WEBHOOK_HANDLERS.get(event_type)
    if handler is None:
        logger.debug("unhandled_stripe_event", extra={"type": event_type})
        return

    await handler(db, data_obj)
    logger.info("stripe_webhook_handled", extra={"type": event_type})


async def _handle_subscription_created(db: AsyncSession, sub_obj: Any) -> None:
    """Handle subscription.created — link Stripe sub to firm."""
    firm_id = sub_obj.metadata.get("firm_id") if sub_obj.metadata else None
    if not firm_id:
        logger.warning("subscription_created_no_firm_id")
        return

    import uuid as uuid_mod

    try:
        firm_uuid = uuid_mod.UUID(firm_id)
    except (ValueError, AttributeError):
        logger.error("subscription_created_invalid_firm_id", extra={"firm_id": firm_id})
        return
    sub = await get_or_create_subscription(db, firm_id=firm_uuid)

    tier_str = sub_obj.metadata.get("tier", "starter")
    tier = (
        SubscriptionTier(tier_str)
        if tier_str in SubscriptionTier.__members__
        else SubscriptionTier.starter
    )

    sub.stripe_subscription_id = sub_obj.id
    sub.status = _map_stripe_status(sub_obj.status)
    sub.tier = tier

    if sub_obj.items and sub_obj.items.data:
        price = sub_obj.items.data[0].price
        sub.stripe_price_id = price.id
        sub.billing_interval = (
            BillingInterval.year
            if price.recurring and price.recurring.interval == "year"
            else BillingInterval.month
        )

    sub.current_period_start = _ts_to_dt(sub_obj.current_period_start)
    sub.current_period_end = _ts_to_dt(sub_obj.current_period_end)
    sub.cancel_at_period_end = bool(sub_obj.cancel_at_period_end)
    sub.trial_end = _ts_to_dt(getattr(sub_obj, "trial_end", None))

    # Update firm tier
    firm_result = await db.execute(select(Firm).where(Firm.id == firm_uuid))
    firm = firm_result.scalar_one_or_none()
    if firm:
        firm.subscription_tier = tier

    await db.flush()

    await event_logger.log(
        db,
        matter_id=firm_uuid,
        actor_id=None,
        actor_type=ActorType.system,
        entity_type="subscription",
        entity_id=firm_uuid,
        action="subscription_created",
        metadata={"tier": tier_str, "stripe_sub_id": sub_obj.id},
    )


async def _handle_subscription_updated(db: AsyncSession, sub_obj: Any) -> None:
    """Handle subscription.updated — tier changes, cancellation, period renewal."""
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == sub_obj.id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        logger.warning(
            "subscription_updated_not_found",
            extra={"stripe_sub_id": sub_obj.id},
        )
        return

    old_status = sub.status
    sub.status = _map_stripe_status(sub_obj.status)
    sub.current_period_start = _ts_to_dt(sub_obj.current_period_start)
    sub.current_period_end = _ts_to_dt(sub_obj.current_period_end)
    sub.cancel_at_period_end = bool(sub_obj.cancel_at_period_end)
    sub.canceled_at = _ts_to_dt(getattr(sub_obj, "canceled_at", None))
    sub.trial_end = _ts_to_dt(getattr(sub_obj, "trial_end", None))

    # Detect tier change from price
    if sub_obj.items and sub_obj.items.data:
        price = sub_obj.items.data[0].price
        sub.stripe_price_id = price.id
        sub.billing_interval = (
            BillingInterval.year
            if price.recurring and price.recurring.interval == "year"
            else BillingInterval.month
        )

    # Update tier from metadata if present
    if sub_obj.metadata and sub_obj.metadata.get("tier"):
        tier_str = sub_obj.metadata["tier"]
        if tier_str in SubscriptionTier.__members__:
            sub.tier = SubscriptionTier(tier_str)
            # Sync to firm
            firm_result = await db.execute(select(Firm).where(Firm.id == sub.firm_id))
            firm = firm_result.scalar_one_or_none()
            if firm:
                firm.subscription_tier = sub.tier

    # Clear grace period if payment succeeded
    if old_status == SubscriptionStatus.past_due and sub.status == SubscriptionStatus.active:
        sub.grace_period_end = None
        sub.last_payment_error = None
        sub.failed_payment_count = 0

    await db.flush()

    await event_logger.log(
        db,
        matter_id=uuid.UUID(sub.firm_id) if isinstance(sub.firm_id, str) else sub.firm_id,
        actor_id=None,
        actor_type=ActorType.system,
        entity_type="subscription",
        entity_id=uuid.UUID(sub.firm_id) if isinstance(sub.firm_id, str) else sub.firm_id,
        action="subscription_updated",
        metadata={
            "status": sub.status.value,
            "tier": sub.tier.value,
            "cancel_at_period_end": sub.cancel_at_period_end,
        },
    )


async def _handle_subscription_deleted(db: AsyncSession, sub_obj: Any) -> None:
    """Handle subscription.deleted — mark as canceled."""
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == sub_obj.id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        return

    sub.status = SubscriptionStatus.canceled
    sub.canceled_at = datetime.now(UTC)

    # Downgrade firm tier to starter
    firm_result = await db.execute(select(Firm).where(Firm.id == sub.firm_id))
    firm = firm_result.scalar_one_or_none()
    if firm:
        firm.subscription_tier = SubscriptionTier.starter

    await db.flush()

    await event_logger.log(
        db,
        matter_id=uuid.UUID(sub.firm_id) if isinstance(sub.firm_id, str) else sub.firm_id,
        actor_id=None,
        actor_type=ActorType.system,
        entity_type="subscription",
        entity_id=uuid.UUID(sub.firm_id) if isinstance(sub.firm_id, str) else sub.firm_id,
        action="subscription_canceled",
    )


async def _handle_invoice_paid(db: AsyncSession, invoice_obj: Any) -> None:
    """Handle invoice.paid — record payment, clear dunning state."""
    customer_id = invoice_obj.customer
    if not customer_id:
        return

    result = await db.execute(select(Firm).where(Firm.stripe_customer_id == customer_id))
    firm = result.scalar_one_or_none()
    if firm is None:
        return

    sub_result = await db.execute(select(Subscription).where(Subscription.firm_id == firm.id))
    sub = sub_result.scalar_one_or_none()
    if sub is None:
        return

    sub.last_invoice_amount = invoice_obj.amount_paid
    # Prefer Stripe's timestamp over local time for accuracy
    paid_ts = None
    transitions = getattr(invoice_obj, "status_transitions", None)
    if transitions:
        paid_ts = getattr(transitions, "paid_at", None)
    sub.last_invoice_paid_at = _ts_to_dt(paid_ts) or datetime.now(UTC)
    sub.last_payment_error = None
    sub.failed_payment_count = 0
    sub.grace_period_end = None

    if sub.status == SubscriptionStatus.past_due:
        sub.status = SubscriptionStatus.active

    await db.flush()


async def _handle_invoice_payment_failed(db: AsyncSession, invoice_obj: Any) -> None:
    """Handle invoice.payment_failed — start dunning / grace period."""
    customer_id = invoice_obj.customer
    if not customer_id:
        return

    result = await db.execute(select(Firm).where(Firm.stripe_customer_id == customer_id))
    firm = result.scalar_one_or_none()
    if firm is None:
        return

    sub_result = await db.execute(select(Subscription).where(Subscription.firm_id == firm.id))
    sub = sub_result.scalar_one_or_none()
    if sub is None:
        return

    sub.failed_payment_count += 1
    sub.status = SubscriptionStatus.past_due

    # Extract payment error message
    if hasattr(invoice_obj, "last_finalization_error") and invoice_obj.last_finalization_error:
        sub.last_payment_error = str(
            invoice_obj.last_finalization_error.get("message", "Payment failed")
        )
    else:
        sub.last_payment_error = "Payment failed"

    # Set grace period on first failure
    if sub.grace_period_end is None:
        sub.grace_period_end = datetime.now(UTC) + timedelta(days=GRACE_PERIOD_DAYS)

    await db.flush()

    await event_logger.log(
        db,
        matter_id=firm.id,
        actor_id=None,
        actor_type=ActorType.system,
        entity_type="subscription",
        entity_id=firm.id,
        action="payment_failed",
        metadata={
            "failed_count": sub.failed_payment_count,
            "grace_period_end": (
                sub.grace_period_end.isoformat() if sub.grace_period_end else None
            ),
        },
    )

    # TODO: Send dunning email to firm owners
    logger.warning(
        "payment_failed_dunning",
        extra={
            "firm_id": str(firm.id),
            "failed_count": sub.failed_payment_count,
        },
    )


# ─── Webhook handler dispatch table ─────────────────────────────────────────

_WEBHOOK_HANDLERS: dict[str, Any] = {
    "customer.subscription.created": _handle_subscription_created,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
    "invoice.paid": _handle_invoice_paid,
    "invoice.payment_failed": _handle_invoice_payment_failed,
}


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _map_stripe_status(status: str) -> SubscriptionStatus:
    """Map Stripe subscription status string to our enum."""
    mapping = {
        "trialing": SubscriptionStatus.trialing,
        "active": SubscriptionStatus.active,
        "past_due": SubscriptionStatus.past_due,
        "canceled": SubscriptionStatus.canceled,
        "unpaid": SubscriptionStatus.unpaid,
        "incomplete": SubscriptionStatus.incomplete,
        "incomplete_expired": SubscriptionStatus.canceled,
        "paused": SubscriptionStatus.paused,
    }
    return mapping.get(status, SubscriptionStatus.active)


def _ts_to_dt(ts: int | None) -> datetime | None:
    """Convert a Unix timestamp to a timezone-aware datetime."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=UTC)
