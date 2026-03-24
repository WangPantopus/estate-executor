"""Unit tests for billing_service — tier limits, status mapping, helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.models.enums import BillingInterval, SubscriptionStatus, SubscriptionTier
from app.services.billing_service import (
    GRACE_PERIOD_DAYS,
    TIER_CONFIG,
    _check_access_allowed,
    _map_stripe_status,
    _ts_to_dt,
    get_all_tier_limits,
    get_tier_limits,
)


# ─── Tier config tests ───────────────────────────────────────────────────────


class TestTierConfig:
    """Verify tier definitions are correct."""

    def test_all_tiers_present(self):
        assert "starter" in TIER_CONFIG
        assert "professional" in TIER_CONFIG
        assert "growth" in TIER_CONFIG
        assert "enterprise" in TIER_CONFIG

    def test_starter_limits(self):
        limits = TIER_CONFIG["starter"]
        assert limits.max_matters == 10
        assert limits.max_users == 2
        assert limits.monthly_price_cents == 4900
        assert limits.annual_price_cents == 47000

    def test_professional_limits(self):
        limits = TIER_CONFIG["professional"]
        assert limits.max_matters == 50
        assert limits.max_users == 5
        assert limits.monthly_price_cents == 14900

    def test_growth_limits(self):
        limits = TIER_CONFIG["growth"]
        assert limits.max_matters == 200
        assert limits.max_users == 15
        assert limits.monthly_price_cents == 34900

    def test_enterprise_unlimited(self):
        limits = TIER_CONFIG["enterprise"]
        assert limits.max_matters == 999999
        assert limits.max_users == 999999

    def test_annual_discount(self):
        """Annual pricing should be less than 12x monthly."""
        for tier_name, limits in TIER_CONFIG.items():
            if tier_name == "enterprise":
                continue
            yearly_from_monthly = limits.monthly_price_cents * 12
            assert limits.annual_price_cents < yearly_from_monthly, (
                f"{tier_name}: annual ({limits.annual_price_cents}) should be "
                f"less than 12x monthly ({yearly_from_monthly})"
            )

    def test_tiers_increase_monotonically(self):
        """Each higher tier should have higher limits."""
        order = ["starter", "professional", "growth"]
        for i in range(len(order) - 1):
            lower = TIER_CONFIG[order[i]]
            higher = TIER_CONFIG[order[i + 1]]
            assert higher.max_matters > lower.max_matters
            assert higher.max_users > lower.max_users
            assert higher.monthly_price_cents > lower.monthly_price_cents


class TestGetTierLimits:
    def test_known_tier(self):
        limits = get_tier_limits("professional")
        assert limits.max_matters == 50

    def test_unknown_tier_defaults_to_starter(self):
        limits = get_tier_limits("unknown_tier")
        assert limits.max_matters == 10

    def test_get_all_tier_limits(self):
        all_limits = get_all_tier_limits()
        assert len(all_limits) == 4
        assert "starter" in all_limits


# ─── Status mapping tests ────────────────────────────────────────────────────


class TestMapStripeStatus:
    def test_active(self):
        assert _map_stripe_status("active") == SubscriptionStatus.active

    def test_trialing(self):
        assert _map_stripe_status("trialing") == SubscriptionStatus.trialing

    def test_past_due(self):
        assert _map_stripe_status("past_due") == SubscriptionStatus.past_due

    def test_canceled(self):
        assert _map_stripe_status("canceled") == SubscriptionStatus.canceled

    def test_unpaid(self):
        assert _map_stripe_status("unpaid") == SubscriptionStatus.unpaid

    def test_incomplete(self):
        assert _map_stripe_status("incomplete") == SubscriptionStatus.incomplete

    def test_incomplete_expired_maps_to_canceled(self):
        assert _map_stripe_status("incomplete_expired") == SubscriptionStatus.canceled

    def test_paused(self):
        assert _map_stripe_status("paused") == SubscriptionStatus.paused

    def test_unknown_defaults_to_active(self):
        assert _map_stripe_status("some_new_status") == SubscriptionStatus.active


# ─── Timestamp helper tests ──────────────────────────────────────────────────


class TestTimestampHelper:
    def test_none_returns_none(self):
        assert _ts_to_dt(None) is None

    def test_valid_timestamp(self):
        ts = 1711234567
        result = _ts_to_dt(ts)
        assert result is not None
        assert result.tzinfo is not None
        assert isinstance(result, datetime)

    def test_zero_timestamp(self):
        result = _ts_to_dt(0)
        assert result is not None
        assert result.year == 1970


# ─── Access control tests ────────────────────────────────────────────────────


class _FakeSubscription:
    """Minimal mock for access control tests."""

    def __init__(
        self,
        status: str = "active",
        grace_period_end: datetime | None = None,
    ):
        self.status = SubscriptionStatus(status)
        self.grace_period_end = grace_period_end


class TestCheckAccessAllowed:
    def test_active_allows_access(self):
        sub = _FakeSubscription(status="active")
        _check_access_allowed(sub)  # should not raise

    def test_trialing_allows_access(self):
        sub = _FakeSubscription(status="trialing")
        _check_access_allowed(sub)

    def test_canceled_blocks_access(self):
        sub = _FakeSubscription(status="canceled")
        with pytest.raises(Exception, match="inactive"):
            _check_access_allowed(sub)

    def test_unpaid_blocks_access(self):
        sub = _FakeSubscription(status="unpaid")
        with pytest.raises(Exception, match="inactive"):
            _check_access_allowed(sub)

    def test_past_due_within_grace_allows(self):
        future = datetime.now(UTC) + timedelta(days=3)
        sub = _FakeSubscription(status="past_due", grace_period_end=future)
        _check_access_allowed(sub)  # should not raise

    def test_past_due_expired_grace_blocks(self):
        past = datetime.now(UTC) - timedelta(days=1)
        sub = _FakeSubscription(status="past_due", grace_period_end=past)
        with pytest.raises(Exception, match="overdue"):
            _check_access_allowed(sub)

    def test_past_due_no_grace_allows(self):
        """If grace period hasn't been set yet, allow access."""
        sub = _FakeSubscription(status="past_due", grace_period_end=None)
        _check_access_allowed(sub)  # should not raise


# ─── Enum tests ──────────────────────────────────────────────────────────────


class TestBillingEnums:
    def test_subscription_status_values(self):
        assert SubscriptionStatus.active.value == "active"
        assert SubscriptionStatus.past_due.value == "past_due"
        assert SubscriptionStatus.canceled.value == "canceled"

    def test_billing_interval_values(self):
        assert BillingInterval.month.value == "month"
        assert BillingInterval.year.value == "year"

    def test_subscription_tier_has_all(self):
        tiers = {t.value for t in SubscriptionTier}
        assert tiers == {"starter", "professional", "growth", "enterprise"}


class TestGracePeriod:
    def test_grace_period_days_is_reasonable(self):
        assert 3 <= GRACE_PERIOD_DAYS <= 14
