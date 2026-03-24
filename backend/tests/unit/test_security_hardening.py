"""Unit tests for security hardening: rate limiting, CSRF, security headers, secrets."""

from __future__ import annotations

import hashlib
import hmac
import time
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Rate limiter tests
# ---------------------------------------------------------------------------


class TestRateLimiter:
    """Tests for the sliding-window rate limiter."""

    def _make_request(
        self,
        path: str = "/api/v1/firms/abc/matters",
        method: str = "GET",
        user_id: str | None = None,
        client_ip: str = "127.0.0.1",
    ) -> MagicMock:
        request = MagicMock()
        request.url.path = path
        request.method = method
        request.headers = {}
        request.client.host = client_ip

        state = MagicMock()
        state.user_id = user_id
        request.state = state

        return request

    def test_resolve_tier_auth_endpoints(self) -> None:
        from app.services.rate_limiter import _resolve_tier

        assert _resolve_tier("/api/v1/auth/login", "POST") == "strict"
        assert _resolve_tier("/api/v1/auth/callback", "GET") == "strict"

    def test_resolve_tier_privacy_endpoints(self) -> None:
        from app.services.rate_limiter import _resolve_tier

        firm_id = "00000000-0000-0000-0000-000000000001"
        assert _resolve_tier(f"/api/v1/firms/{firm_id}/privacy/request", "POST") == "strict"

    def test_resolve_tier_health_falls_to_standard(self) -> None:
        """Health endpoints are skipped at middleware level, but if called directly
        the tier resolver returns standard (the default for GET)."""
        from app.services.rate_limiter import _resolve_tier

        assert _resolve_tier("/health", "GET") == "standard"
        assert _resolve_tier("/api/v1/health", "GET") == "standard"

    def test_resolve_tier_templates_relaxed(self) -> None:
        from app.services.rate_limiter import _resolve_tier

        assert _resolve_tier("/api/v1/templates", "GET") == "relaxed"
        assert _resolve_tier("/api/v1/templates/CA", "GET") == "relaxed"

    def test_resolve_tier_write_methods(self) -> None:
        from app.services.rate_limiter import _resolve_tier

        assert _resolve_tier("/api/v1/firms/123/matters", "POST") == "write"
        assert _resolve_tier("/api/v1/firms/123/matters/456/tasks", "PUT") == "write"
        assert _resolve_tier("/api/v1/firms/123/matters/456/tasks/789", "DELETE") == "write"

    def test_resolve_tier_standard_reads(self) -> None:
        from app.services.rate_limiter import _resolve_tier

        assert _resolve_tier("/api/v1/firms/123/matters", "GET") == "standard"

    def test_identifier_uses_user_id_when_available(self) -> None:
        from app.services.rate_limiter import _get_identifier

        request = self._make_request(user_id="user-123")
        assert _get_identifier(request) == "user:user-123"

    def test_identifier_falls_back_to_ip(self) -> None:
        from app.services.rate_limiter import _get_identifier

        request = self._make_request(client_ip="10.0.0.1")
        assert _get_identifier(request) == "ip:10.0.0.1"

    def test_identifier_uses_x_forwarded_for(self) -> None:
        from app.services.rate_limiter import _get_identifier

        request = self._make_request()
        request.headers = {"x-forwarded-for": "203.0.113.50, 70.41.3.18"}
        assert _get_identifier(request) == "ip:203.0.113.50"

    @patch("app.services.rate_limiter._get_redis")
    def test_check_rate_limit_allows_under_limit(self, mock_get_redis: MagicMock) -> None:
        from app.core.config import settings
        from app.services.rate_limiter import check_rate_limit

        mock_redis = MagicMock()
        mock_redis.eval.return_value = 55  # remaining
        mock_get_redis.return_value = mock_redis

        request = self._make_request()
        result = check_rate_limit(request)

        assert result["remaining"] == 55
        assert result["limit"] == settings.rate_limit_standard  # standard tier for GET

    @patch("app.services.rate_limiter._get_redis")
    def test_check_rate_limit_raises_on_exceeded(self, mock_get_redis: MagicMock) -> None:
        from app.core.exceptions import RateLimitError
        from app.services.rate_limiter import check_rate_limit

        mock_redis = MagicMock()
        mock_redis.eval.return_value = -1  # exceeded
        mock_get_redis.return_value = mock_redis

        request = self._make_request()
        with pytest.raises(RateLimitError):
            check_rate_limit(request)

    @patch("app.services.rate_limiter._get_redis")
    def test_check_rate_limit_fails_open_on_redis_error(
        self, mock_get_redis: MagicMock
    ) -> None:
        from app.services.rate_limiter import check_rate_limit

        mock_get_redis.side_effect = ConnectionError("Redis down")

        request = self._make_request()
        result = check_rate_limit(request)

        # Should fail open
        assert result["remaining"] == result["limit"]


# ---------------------------------------------------------------------------
# CSRF protection tests
# ---------------------------------------------------------------------------


class TestCSRFProtection:
    """Tests for CSRF token generation, signing, and verification."""

    def test_generate_csrf_token_is_unique(self) -> None:
        from app.core.security_middleware import _generate_csrf_token

        tokens = {_generate_csrf_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_create_signed_token_format(self) -> None:
        from app.core.security_middleware import _create_signed_token

        signed = _create_signed_token("test-secret")
        parts = signed.split(":")
        assert len(parts) == 3
        # timestamp:token:signature
        assert int(parts[0]) > 0
        assert len(parts[1]) > 0
        assert len(parts[2]) == 64  # SHA256 hex

    def test_verify_valid_token(self) -> None:
        """Double-submit: cookie and header carry the same signed value."""
        from app.core.security_middleware import _create_signed_token, _verify_signed_token

        secret = "test-secret-key"
        signed = _create_signed_token(secret)
        # Frontend sends the full signed value from cookie as the header
        assert _verify_signed_token(signed, signed, secret) is True

    def test_verify_rejects_wrong_header_token(self) -> None:
        from app.core.security_middleware import _create_signed_token, _verify_signed_token

        secret = "test-secret-key"
        signed = _create_signed_token(secret)
        assert _verify_signed_token(signed, "wrong-token", secret) is False

    def test_verify_rejects_different_tokens(self) -> None:
        from app.core.security_middleware import _create_signed_token, _verify_signed_token

        secret = "test-secret-key"
        signed1 = _create_signed_token(secret)
        signed2 = _create_signed_token(secret)
        # Two different tokens should not validate against each other
        assert _verify_signed_token(signed1, signed2, secret) is False

    def test_verify_rejects_wrong_secret(self) -> None:
        from app.core.security_middleware import _create_signed_token, _verify_signed_token

        signed = _create_signed_token("real-secret")
        # Even if cookie==header, wrong secret should fail signature check
        # But first, cookie==header comparison will pass since they're the same...
        # Actually with wrong secret the signature check fails
        # We need to craft a token signed with wrong secret
        signed_wrong = _create_signed_token("wrong-secret")
        assert _verify_signed_token(signed, signed_wrong, "real-secret") is False

    def test_verify_rejects_expired_token(self) -> None:
        from app.core.security_middleware import (
            _CSRF_TOKEN_EXPIRY,
            _create_signed_token,
            _verify_signed_token,
        )

        secret = "test-secret"
        signed = _create_signed_token(secret)

        # Tamper with timestamp to make it expired, re-sign to keep signature valid
        parts = signed.split(":")
        old_timestamp = str(int(time.time()) - _CSRF_TOKEN_EXPIRY - 100)
        message = f"{old_timestamp}:{parts[1]}"
        new_sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        expired_signed = f"{old_timestamp}:{parts[1]}:{new_sig}"

        # Both cookie and header carry the expired token
        assert _verify_signed_token(expired_signed, expired_signed, secret) is False

    def test_verify_rejects_tampered_signature(self) -> None:
        from app.core.security_middleware import _create_signed_token, _verify_signed_token

        secret = "test-secret"
        signed = _create_signed_token(secret)

        parts = signed.split(":")
        tampered = f"{parts[0]}:{parts[1]}:{'a' * 64}"
        # Both cookie and header have the tampered value
        assert _verify_signed_token(tampered, tampered, secret) is False

    def test_verify_rejects_malformed_input(self) -> None:
        from app.core.security_middleware import _verify_signed_token

        assert _verify_signed_token("not-valid", "not-valid", "secret") is False
        assert _verify_signed_token("", "", "secret") is False
        assert _verify_signed_token("a:b", "a:b", "secret") is False


# ---------------------------------------------------------------------------
# Security headers tests
# ---------------------------------------------------------------------------


class TestSecurityHeaders:
    """Tests for Content-Security-Policy and other security headers."""

    def test_csp_build(self) -> None:
        from app.core.security_middleware import SecurityHeadersMiddleware

        middleware = SecurityHeadersMiddleware(app=MagicMock())
        csp = middleware._build_csp()

        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp
        assert "base-uri 'self'" in csp
        assert "form-action 'self'" in csp
        # WebSocket support
        assert "connect-src 'self' ws: wss:" in csp

    def test_csp_contains_upgrade_insecure(self) -> None:
        from app.core.security_middleware import SecurityHeadersMiddleware

        middleware = SecurityHeadersMiddleware(app=MagicMock())
        csp = middleware._build_csp()

        assert "upgrade-insecure-requests" in csp


# ---------------------------------------------------------------------------
# Secrets management validation tests
# ---------------------------------------------------------------------------


class TestSecretsValidation:
    """Tests for production secret validation."""

    def test_development_returns_no_warnings(self) -> None:
        from app.core.config import Settings

        s = Settings(app_env="development")
        assert s.validate_production_secrets() == []

    def test_production_warns_default_secret_key(self) -> None:
        from app.core.config import Settings

        s = Settings(
            app_env="production",
            environment="production",
            app_secret_key="change-me-to-a-random-secret",
        )
        warnings = s.validate_production_secrets()
        assert any("APP_SECRET_KEY" in w for w in warnings)

    def test_production_warns_missing_encryption_key(self) -> None:
        from app.core.config import Settings

        s = Settings(
            app_env="production",
            environment="production",
            encryption_master_key="",
        )
        warnings = s.validate_production_secrets()
        assert any("ENCRYPTION_MASTER_KEY" in w for w in warnings)

    def test_production_warns_mock_auth_enabled(self) -> None:
        from app.core.config import Settings

        s = Settings(
            app_env="production",
            environment="production",
            e2e_mock_auth=True,
        )
        warnings = s.validate_production_secrets()
        assert any("E2E_MOCK_AUTH" in w for w in warnings)

    def test_production_warns_localhost_cors(self) -> None:
        from app.core.config import Settings

        s = Settings(
            app_env="production",
            environment="production",
            backend_cors_origins=["http://localhost:3000"],
        )
        warnings = s.validate_production_secrets()
        assert any("CORS" in w for w in warnings)


# ---------------------------------------------------------------------------
# QBO query injection prevention tests
# ---------------------------------------------------------------------------


class TestQBOQuerySafety:
    """Tests that QuickBooks query building prevents injection."""

    def test_journal_entry_rejects_invalid_filter_field(self) -> None:
        from app.services.quickbooks_client import QuickBooksAPI

        client = QuickBooksAPI.__new__(QuickBooksAPI)
        with pytest.raises(ValueError, match="Invalid filter field"):
            import asyncio

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    client.query_journal_entries(filter_field="'; DROP TABLE --")
                )
            finally:
                loop.close()

    def test_journal_entry_rejects_invalid_operator(self) -> None:
        from app.services.quickbooks_client import QuickBooksAPI

        client = QuickBooksAPI.__new__(QuickBooksAPI)
        with pytest.raises(ValueError, match="Invalid filter operator"):
            import asyncio

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    client.query_journal_entries(
                        filter_field="TxnDate",
                        filter_operator="'; DROP--",
                    )
                )
            finally:
                loop.close()

    def test_account_query_rejects_invalid_type(self) -> None:
        from app.services.quickbooks_client import QuickBooksAPI

        client = QuickBooksAPI.__new__(QuickBooksAPI)
        with pytest.raises(ValueError, match="Invalid QBO account type"):
            import asyncio

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    client.query_accounts(account_type="'; DROP TABLE accounts--")
                )
            finally:
                loop.close()


# ---------------------------------------------------------------------------
# XSS sanitization tests
# ---------------------------------------------------------------------------


class TestXSSSanitization:
    """Test that the sanitizeSnippet approach is robust (backend-side validation)."""

    def test_jinja2_autoescape_is_enabled(self) -> None:
        """Verify the email template engine has autoescape enabled."""
        from app.services.email_service import _jinja_env

        # The environment should autoescape HTML files
        assert _jinja_env.autoescape is True or callable(_jinja_env.autoescape)
