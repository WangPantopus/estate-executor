"""Unit tests for API key and webhook services."""

from __future__ import annotations

import hashlib

import pytest


class TestAPIKeyGeneration:
    def test_generate_raw_key_format(self):
        from app.services.api_key_service import _generate_raw_key

        key = _generate_raw_key()
        assert key.startswith("ee_live_")
        assert len(key) == 56  # "ee_live_" (8) + 48 hex chars

    def test_generate_raw_key_uniqueness(self):
        from app.services.api_key_service import _generate_raw_key

        keys = {_generate_raw_key() for _ in range(50)}
        assert len(keys) == 50

    def test_hash_key(self):
        from app.services.api_key_service import _hash_key

        key = "ee_live_abc123"
        hashed = _hash_key(key)
        assert hashed == hashlib.sha256(key.encode()).hexdigest()
        assert len(hashed) == 64

    def test_extract_prefix(self):
        from app.services.api_key_service import _extract_prefix

        key = "ee_live_abc123def456"
        prefix = _extract_prefix(key)
        assert prefix == "ee_live_abc1"
        assert len(prefix) == 12


class TestAPIKeySchemas:
    def test_create_schema_defaults(self):
        from app.schemas.api_keys import APIKeyCreate

        create = APIKeyCreate(name="Test Key")
        assert create.scopes == ["read"]
        assert create.rate_limit_per_minute == 60
        assert create.expires_at is None

    def test_create_schema_custom(self):
        from app.schemas.api_keys import APIKeyCreate

        create = APIKeyCreate(
            name="Full Access",
            scopes=["read", "write", "webhooks"],
            rate_limit_per_minute=120,
        )
        assert create.scopes == ["read", "write", "webhooks"]
        assert create.rate_limit_per_minute == 120

    def test_response_excludes_hash(self):
        from datetime import UTC, datetime
        from uuid import uuid4

        from app.schemas.api_keys import APIKeyResponse

        resp = APIKeyResponse(
            id=uuid4(),
            firm_id=uuid4(),
            name="Test",
            key_prefix="ee_live_xxxx",
            scopes=["read"],
            rate_limit_per_minute=60,
            is_active=True,
            created_by=uuid4(),
            total_requests=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert not hasattr(resp, "key_hash")
        assert not hasattr(resp, "raw_key")


class TestWebhookSchemas:
    def test_create_schema(self):
        from app.schemas.webhooks import WebhookCreate

        create = WebhookCreate(
            url="https://example.com/webhook",
            events=["matter.created", "task.updated"],
        )
        assert len(create.events) == 2

    def test_update_schema_partial(self):
        from app.schemas.webhooks import WebhookUpdate

        update = WebhookUpdate(is_active=False)
        dumped = update.model_dump(exclude_unset=True)
        assert dumped == {"is_active": False}

    def test_delivery_response(self):
        from datetime import UTC, datetime
        from uuid import uuid4

        from app.schemas.webhooks import WebhookDeliveryResponse

        delivery = WebhookDeliveryResponse(
            id=uuid4(),
            webhook_id=uuid4(),
            event_type="matter.created",
            payload={"matter_id": "123"},
            status_code=200,
            response_body="OK",
            success=True,
            duration_ms=150,
            attempt=1,
            created_at=datetime.now(UTC),
        )
        assert delivery.success is True
        assert delivery.duration_ms == 150


class TestWebhookServiceHelpers:
    def test_generate_secret(self):
        from app.services.webhook_service import _generate_secret

        secret = _generate_secret()
        assert secret.startswith("whsec_")
        assert len(secret) == 54  # "whsec_" (6) + 48 hex chars

    def test_sign_payload(self):
        from app.services.webhook_service import _sign_payload

        sig = _sign_payload("secret", '{"test": true}')
        assert len(sig) == 64  # SHA-256 hex digest

    def test_sign_payload_consistency(self):
        from app.services.webhook_service import _sign_payload

        sig1 = _sign_payload("secret", "payload")
        sig2 = _sign_payload("secret", "payload")
        assert sig1 == sig2

    def test_sign_payload_different_secrets(self):
        from app.services.webhook_service import _sign_payload

        sig1 = _sign_payload("secret1", "payload")
        sig2 = _sign_payload("secret2", "payload")
        assert sig1 != sig2

    def test_supported_events(self):
        from app.services.webhook_service import get_supported_events

        events = get_supported_events()
        assert "matter.created" in events
        assert "task.updated" in events
        assert "document.uploaded" in events
        assert len(events) >= 15

    def test_supported_events_returns_copy(self):
        from app.services.webhook_service import get_supported_events

        events1 = get_supported_events()
        events2 = get_supported_events()
        events1.append("fake.event")
        assert "fake.event" not in events2
