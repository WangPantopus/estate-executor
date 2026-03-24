"""Security middleware: rate limiting, CSRF protection, and security headers."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

if TYPE_CHECKING:
    from fastapi import Request, Response

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate Limiting Middleware
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply Redis-based sliding-window rate limiting to all endpoints.

    Rate limit info is returned in standard headers:
    - X-RateLimit-Limit
    - X-RateLimit-Remaining
    - Retry-After (on 429)
    """

    # Paths that skip rate limiting entirely
    _SKIP_PATHS = frozenset({"/health", "/api/v1/health", "/docs", "/openapi.json", "/redoc"})

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)  # type: ignore[no-any-return]

        if not settings.rate_limit_enabled:
            return await call_next(request)  # type: ignore[no-any-return]

        from app.core.exceptions import RateLimitError
        from app.services.rate_limiter import check_rate_limit

        try:
            info = check_rate_limit(request)
        except RateLimitError as exc:
            return JSONResponse(
                status_code=429,
                content={
                    "type": "about:blank",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": exc.detail,
                    "instance": request.url.path,
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": "0",
                    "X-RateLimit-Remaining": "0",
                },
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        return response


# ---------------------------------------------------------------------------
# Security Headers Middleware (CSP, HSTS, X-Frame-Options, etc.)
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add comprehensive security headers to all responses.

    Includes Content-Security-Policy, Strict-Transport-Security,
    X-Content-Type-Options, X-Frame-Options, and more.
    """

    # CSP directives — strict by default, can be relaxed via settings
    _CSP_DIRECTIVES: dict[str, str] = {
        "default-src": "'self'",
        "script-src": "'self'",
        "style-src": "'self' 'unsafe-inline'",  # Many UI frameworks need inline styles
        "img-src": "'self' data: https:",
        "font-src": "'self' data:",
        "connect-src": "'self' ws: wss:",
        "frame-ancestors": "'none'",
        "base-uri": "'self'",
        "form-action": "'self'",
        "object-src": "'none'",
        "upgrade-insecure-requests": "",
    }

    def _build_csp(self) -> str:
        """Build the Content-Security-Policy header value."""
        parts = []
        for directive, value in self._CSP_DIRECTIVES.items():
            if value:
                parts.append(f"{directive} {value}")
            else:
                parts.append(directive)
        return "; ".join(parts)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        response: Response = await call_next(request)

        # Content Security Policy
        response.headers["Content-Security-Policy"] = self._build_csp()

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy — don't leak URLs to third parties
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy — disable unnecessary browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # HSTS in production (1 year, include subdomains)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Remove server identification header if present
        if "Server" in response.headers:
            del response.headers["Server"]

        return response


# ---------------------------------------------------------------------------
# CSRF Protection Middleware
# ---------------------------------------------------------------------------

_CSRF_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Paths that are exempt from CSRF (webhooks receive external callbacks)
_CSRF_EXEMPT_PREFIXES = (
    "/api/v1/webhooks",
    "/api/v1/auth",
    "/health",
    "/api/v1/health",
    "/docs",
    "/openapi.json",
    "/ws",
)

# CSRF token settings
_CSRF_TOKEN_HEADER = "X-CSRF-Token"
_CSRF_COOKIE_NAME = "csrf_token"
_CSRF_TOKEN_EXPIRY = 3600 * 8  # 8 hours


def _generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


def _create_signed_token(secret_key: str) -> str:
    """Create a CSRF token with HMAC signature.

    Returns signed_value = timestamp:token:signature.
    The full signed value is stored in the cookie AND sent by the frontend
    as the X-CSRF-Token header (standard double-submit cookie pattern).
    """
    token = _generate_csrf_token()
    timestamp = str(int(time.time()))
    message = f"{timestamp}:{token}"
    signature = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{timestamp}:{token}:{signature}"


def _verify_signed_token(signed_value: str, header_token: str, secret_key: str) -> bool:
    """Verify the CSRF token: cookie and header must match, signature must be valid."""
    try:
        # Cookie and header must be identical (double-submit)
        if not hmac.compare_digest(signed_value, header_token):
            return False

        parts = signed_value.split(":")
        if len(parts) != 3:
            return False
        timestamp_str, cookie_token, signature = parts

        # Check expiry
        timestamp = int(timestamp_str)
        if time.time() - timestamp > _CSRF_TOKEN_EXPIRY:
            return False

        # Verify HMAC signature to ensure token was issued by this server
        message = f"{timestamp_str}:{cookie_token}"
        expected_sig = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected_sig)
    except (ValueError, TypeError):
        return False


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie CSRF protection.

    For state-changing requests (POST, PUT, PATCH, DELETE):
    1. A signed CSRF token is set in a cookie on first request
    2. The client must send the token back in X-CSRF-Token header
    3. Cookie value and header value are compared with timing-safe comparison

    API-key authenticated requests and webhook endpoints are exempt.
    SPA architecture: the frontend reads the cookie and sends it as a header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        if not settings.csrf_enabled:
            return await call_next(request)  # type: ignore[no-any-return]

        # Skip for exempt paths
        for prefix in _CSRF_EXEMPT_PREFIXES:
            if request.url.path.startswith(prefix):
                return await call_next(request)  # type: ignore[no-any-return]

        # Skip for API key requests (machine-to-machine)
        if request.headers.get("X-API-Key"):
            return await call_next(request)  # type: ignore[no-any-return]

        secret_key = settings.app_secret_key

        # For safe methods, ensure a CSRF cookie is set
        if request.method in _CSRF_SAFE_METHODS:
            response: Response = await call_next(request)

            # Set CSRF cookie if not present
            if _CSRF_COOKIE_NAME not in request.cookies:
                signed_value = _create_signed_token(secret_key)
                response.set_cookie(
                    key=_CSRF_COOKIE_NAME,
                    value=signed_value,
                    httponly=False,  # JS must read this to send as X-CSRF-Token header
                    samesite="strict",
                    secure=settings.is_production,
                    max_age=_CSRF_TOKEN_EXPIRY,
                    path="/",
                )
            return response

        # For state-changing methods, validate CSRF token
        cookie_value = request.cookies.get(_CSRF_COOKIE_NAME)
        header_token = request.headers.get(_CSRF_TOKEN_HEADER)

        if not cookie_value or not header_token:
            return JSONResponse(
                status_code=403,
                content={
                    "type": "about:blank",
                    "title": "Forbidden",
                    "status": 403,
                    "detail": "CSRF token missing",
                    "instance": request.url.path,
                },
            )

        if not _verify_signed_token(cookie_value, header_token, secret_key):
            return JSONResponse(
                status_code=403,
                content={
                    "type": "about:blank",
                    "title": "Forbidden",
                    "status": 403,
                    "detail": "CSRF token invalid",
                    "instance": request.url.path,
                },
            )

        response = await call_next(request)
        return response
