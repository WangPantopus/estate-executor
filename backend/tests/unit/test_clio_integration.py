"""Unit tests for Clio integration — client helpers, sync service, enums."""

from __future__ import annotations

import pytest

from app.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    SyncDirection,
    SyncStatus,
)
from app.services.clio_client import (
    build_authorize_url,
    generate_state,
    token_expires_at,
)


# ─── Enum tests ──────────────────────────────────────────────────────────────


class TestIntegrationEnums:
    def test_provider_values(self):
        assert IntegrationProvider.clio.value == "clio"
        assert IntegrationProvider.quickbooks.value == "quickbooks"
        assert IntegrationProvider.xero.value == "xero"
        assert IntegrationProvider.docusign.value == "docusign"

    def test_status_values(self):
        assert IntegrationStatus.connected.value == "connected"
        assert IntegrationStatus.disconnected.value == "disconnected"
        assert IntegrationStatus.error.value == "error"
        assert IntegrationStatus.pending.value == "pending"

    def test_sync_direction_values(self):
        assert SyncDirection.push.value == "push"
        assert SyncDirection.pull.value == "pull"
        assert SyncDirection.bidirectional.value == "bidirectional"

    def test_sync_status_values(self):
        assert SyncStatus.idle.value == "idle"
        assert SyncStatus.syncing.value == "syncing"
        assert SyncStatus.success.value == "success"
        assert SyncStatus.failed.value == "failed"


# ─── OAuth helpers ───────────────────────────────────────────────────────────


class TestGenerateState:
    def test_generates_string(self):
        state = generate_state()
        assert isinstance(state, str)
        assert len(state) > 20

    def test_unique_each_call(self):
        states = {generate_state() for _ in range(10)}
        assert len(states) == 10


class TestBuildAuthorizeUrl:
    def test_contains_required_params(self):
        url = build_authorize_url("test-state-123")
        assert "response_type=code" in url
        assert "state=test-state-123" in url
        assert "redirect_uri=" in url

    def test_uses_clio_auth_url(self):
        url = build_authorize_url("s")
        assert url.startswith("https://app.clio.com/oauth/authorize")


class TestTokenExpiresAt:
    def test_default_1_hour(self):
        from datetime import UTC, datetime, timedelta

        before = datetime.now(UTC)
        result = token_expires_at(None)
        after = datetime.now(UTC)

        assert before + timedelta(seconds=3599) <= result
        assert result <= after + timedelta(seconds=3601)

    def test_custom_expiry(self):
        from datetime import UTC, datetime, timedelta

        before = datetime.now(UTC)
        result = token_expires_at(7200)
        after = datetime.now(UTC)

        assert before + timedelta(seconds=7199) <= result
        assert result <= after + timedelta(seconds=7201)

    def test_zero_expiry_defaults_to_1h(self):
        from datetime import UTC, datetime, timedelta

        before = datetime.now(UTC)
        result = token_expires_at(0)
        # 0 is falsy, so defaults to 3600 (1 hour)
        assert before + timedelta(seconds=3599) <= result
        assert result <= before + timedelta(seconds=3601)


# ─── ClioAPI client ──────────────────────────────────────────────────────────


class TestClioAPI:
    def test_headers_contain_bearer_token(self):
        from app.services.clio_client import ClioAPI

        api = ClioAPI("test-token-abc")
        headers = api._headers()
        assert headers["Authorization"] == "Bearer test-token-abc"
        assert headers["Content-Type"] == "application/json"

    def test_different_tokens(self):
        from app.services.clio_client import ClioAPI

        api1 = ClioAPI("token-1")
        api2 = ClioAPI("token-2")
        assert api1._headers()["Authorization"] != api2._headers()["Authorization"]


# ─── Sync result structure ───────────────────────────────────────────────────


class TestSyncResultSchema:
    def test_schema_validates(self):
        from app.schemas.integrations import SyncResultResponse

        result = SyncResultResponse(
            resource="matters",
            direction="bidirectional",
            created=5,
            updated=3,
            skipped=2,
            errors=["test error"],
        )
        assert result.resource == "matters"
        assert result.created == 5
        assert len(result.errors) == 1

    def test_schema_defaults(self):
        from app.schemas.integrations import SyncResultResponse

        result = SyncResultResponse(resource="contacts", direction="pull")
        assert result.created == 0
        assert result.updated == 0
        assert result.skipped == 0
        assert result.errors == []


class TestIntegrationConnectionSchema:
    def test_schema_from_dict(self):
        from datetime import UTC, datetime
        from uuid import uuid4

        from app.schemas.integrations import IntegrationConnectionResponse

        data = {
            "id": uuid4(),
            "firm_id": uuid4(),
            "provider": "clio",
            "status": "connected",
            "external_account_id": "12345",
            "external_account_name": "Test Firm",
            "last_sync_at": datetime.now(UTC),
            "last_sync_status": "success",
            "last_sync_error": None,
            "settings": {"auto_sync_matters": True},
            "connected_by": uuid4(),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        resp = IntegrationConnectionResponse(**data)
        assert resp.provider == "clio"
        assert resp.status == "connected"
        assert resp.settings["auto_sync_matters"] is True


class TestClioSettingsSchema:
    def test_partial_update(self):
        from app.schemas.integrations import ClioSettingsUpdate

        update = ClioSettingsUpdate(auto_sync_matters=True)
        dumped = update.model_dump(exclude_unset=True)
        assert dumped == {"auto_sync_matters": True}
        assert "auto_sync_contacts" not in dumped

    def test_all_fields(self):
        from app.schemas.integrations import ClioSettingsUpdate

        update = ClioSettingsUpdate(
            auto_sync_matters=True,
            auto_sync_time_entries=False,
            auto_sync_contacts=True,
            sync_interval_minutes=30,
            default_practice_area="Estate Administration",
        )
        assert update.sync_interval_minutes == 30
