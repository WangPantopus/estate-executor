"""DocuSign eSignature REST API client — OAuth2 and envelope operations."""

from __future__ import annotations

import base64
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


# ─── OAuth2 helpers ──────────────────────────────────────────────────────────


def build_authorize_url(state: str) -> str:
    """Build the DocuSign OAuth2 authorization URL."""
    params = {
        "response_type": "code",
        "scope": "signature impersonation",
        "client_id": settings.docusign_integration_key,
        "redirect_uri": settings.docusign_redirect_uri
        or f"{settings.backend_url}/api/v1/integrations/docusign/callback",
        "state": state,
    }
    return f"{settings.docusign_auth_url}?{urlencode(params)}"


def generate_state() -> str:
    return secrets.token_urlsafe(32)


async def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Exchange authorization code for access/refresh tokens."""
    auth_header = base64.b64encode(
        f"{settings.docusign_integration_key}:{settings.docusign_secret_key}".encode()
    ).decode()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                settings.docusign_token_url,
                headers={"Authorization": f"Basic {auth_header}"},
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                },
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error("docusign_token_exchange_failed", exc_info=True)
            raise ValidationError(detail="Failed to connect to DocuSign.") from e


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """Refresh an expired access token."""
    auth_header = base64.b64encode(
        f"{settings.docusign_integration_key}:{settings.docusign_secret_key}".encode()
    ).decode()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                settings.docusign_token_url,
                headers={"Authorization": f"Basic {auth_header}"},
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error("docusign_token_refresh_failed", exc_info=True)
            raise ValidationError(detail="Failed to refresh DocuSign connection.") from e


def token_expires_at(expires_in: int | None) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=(expires_in or 3600))


async def get_user_info(access_token: str) -> dict[str, Any]:
    """Get the authenticated user's info and account ID."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{settings.docusign_base_url}/oauth/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


# ─── DocuSign eSignature API ─────────────────────────────────────────────────


class DocuSignAPI:
    """Wrapper around DocuSign eSignature REST API v2.1."""

    def __init__(self, access_token: str, account_id: str) -> None:
        self._token = access_token
        self._account_id = account_id
        self._base = f"{settings.docusign_api_base_url}/v2.1/accounts/{account_id}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self._base}{path}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.request(method, url, headers=self._headers(), **kwargs)
            resp.raise_for_status()
            if resp.status_code == 204:
                return {}
            return resp.json()

    async def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, json: dict | None = None) -> dict[str, Any]:
        return await self._request("POST", path, json=json)

    async def _put(self, path: str, json: dict | None = None) -> dict[str, Any]:
        return await self._request("PUT", path, json=json)

    # ── Envelopes ─────────────────────────────────────────────────────────

    async def create_envelope(self, envelope_definition: dict[str, Any]) -> dict[str, Any]:
        """Create and optionally send an envelope."""
        return await self._post("/envelopes", json=envelope_definition)

    async def get_envelope(self, envelope_id: str) -> dict[str, Any]:
        """Get envelope status and details."""
        return await self._get(f"/envelopes/{envelope_id}")

    async def void_envelope(self, envelope_id: str, reason: str) -> dict[str, Any]:
        """Void (cancel) an in-progress envelope."""
        return await self._put(
            f"/envelopes/{envelope_id}",
            json={"status": "voided", "voidedReason": reason},
        )

    async def get_envelope_recipients(self, envelope_id: str) -> dict[str, Any]:
        """Get recipient (signer) status for an envelope."""
        return await self._get(f"/envelopes/{envelope_id}/recipients")

    async def get_envelope_documents(self, envelope_id: str) -> dict[str, Any]:
        """List documents in an envelope."""
        return await self._get(f"/envelopes/{envelope_id}/documents")

    async def download_document(self, envelope_id: str, document_id: str = "combined") -> bytes:
        """Download a completed document from an envelope.

        Uses document_id='combined' to get all docs merged into one PDF.
        """
        url = f"{self._base}/envelopes/{envelope_id}/documents/{document_id}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.content
