"""Unit tests for QuickBooks Online integration — client, helpers, schemas."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.quickbooks_client import (
    QuickBooksAPI,
    build_authorize_url,
    generate_state,
    token_expires_at,
)


class TestQBOOAuth:
    def test_generate_state_unique(self):
        states = {generate_state() for _ in range(10)}
        assert len(states) == 10

    def test_authorize_url_params(self):
        url = build_authorize_url("test-state")
        assert "response_type=code" in url
        assert "state=test-state" in url
        assert "com.intuit.quickbooks.accounting" in url

    def test_authorize_url_starts_with_intuit(self):
        url = build_authorize_url("s")
        assert url.startswith("https://appcenter.intuit.com")

    def test_token_expires_at_default(self):
        before = datetime.now(UTC)
        result = token_expires_at(None)
        assert result >= before + timedelta(seconds=3599)

    def test_token_expires_at_custom(self):
        before = datetime.now(UTC)
        result = token_expires_at(3600)
        assert result >= before + timedelta(seconds=3599)


class TestQuickBooksAPI:
    def test_headers(self):
        api = QuickBooksAPI("test-token", "realm-123")
        headers = api._headers()
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Accept"] == "application/json"

    def test_base_url_includes_realm(self):
        api = QuickBooksAPI("tok", "12345")
        assert "12345" in api._base

    def test_sandbox_url(self):
        api = QuickBooksAPI("tok", "r1")
        assert "sandbox" in api._base or "quickbooks" in api._base


class TestSyncRequestSchema:
    def test_distributions_resource(self):
        from app.schemas.integrations import SyncRequest

        req = SyncRequest(resource="distributions")
        assert req.resource == "distributions"
        assert req.direction == "bidirectional"

    def test_transactions_resource(self):
        from app.schemas.integrations import SyncRequest

        req = SyncRequest(resource="transactions", direction="push")
        assert req.resource == "transactions"

    def test_account_balances_resource(self):
        from app.schemas.integrations import SyncRequest

        req = SyncRequest(resource="account_balances", direction="pull")
        assert req.resource == "account_balances"

    def test_invalid_resource_rejected(self):
        import pytest

        from app.schemas.integrations import SyncRequest

        with pytest.raises(ValueError):
            SyncRequest(resource="invalid_resource")


class TestBankAssetTypes:
    def test_bank_types_defined(self):
        from app.models.enums import AssetType
        from app.services.quickbooks_sync_service import _BANK_ASSET_TYPES

        assert AssetType.bank_account in _BANK_ASSET_TYPES
        assert AssetType.brokerage_account in _BANK_ASSET_TYPES
        assert AssetType.real_estate not in _BANK_ASSET_TYPES
