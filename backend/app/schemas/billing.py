"""Pydantic schemas for Stripe billing endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ─── Tier configuration ──────────────────────────────────────────────────────


class TierLimits(BaseModel):
    """Usage limits per subscription tier."""

    max_matters: int
    max_users: int
    monthly_price_cents: int  # 0 for free / enterprise
    annual_price_cents: int
    stripe_monthly_price_id: str | None = None
    stripe_annual_price_id: str | None = None


# ─── Request schemas ─────────────────────────────────────────────────────────


class CreateCheckoutRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    tier: str  # "starter" | "professional" | "growth"
    billing_interval: str = "month"  # "month" | "year"
    success_url: str | None = None
    cancel_url: str | None = None


class CreatePortalSessionRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    return_url: str | None = None


# ─── Response schemas ────────────────────────────────────────────────────────


class SubscriptionResponse(BaseModel):
    """Full subscription state returned to the frontend."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    firm_id: UUID
    tier: str
    status: str
    billing_interval: str
    stripe_subscription_id: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    canceled_at: datetime | None = None
    trial_end: datetime | None = None
    grace_period_end: datetime | None = None
    last_payment_error: str | None = None
    failed_payment_count: int = 0
    matter_count: int = 0
    user_count: int = 0
    last_invoice_amount: int | None = None
    last_invoice_paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class BillingOverviewResponse(BaseModel):
    """Combined billing info for the settings page."""

    model_config = ConfigDict(strict=True)

    subscription: SubscriptionResponse | None = None
    tier_limits: dict[str, TierLimits]
    usage: UsageResponse


class UsageResponse(BaseModel):
    """Current usage counts vs limits."""

    model_config = ConfigDict(strict=True)

    matter_count: int
    matter_limit: int
    user_count: int
    user_limit: int


class CheckoutSessionResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    checkout_url: str
    session_id: str


class PortalSessionResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    portal_url: str


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    amount_due: int  # cents
    amount_paid: int  # cents
    currency: str
    status: str | None = None
    invoice_url: str | None = None
    invoice_pdf: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    created: datetime | None = None


class InvoiceListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    invoices: list[InvoiceResponse]
    has_more: bool = False
