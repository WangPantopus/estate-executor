"""Clio API client — OAuth2 flow and REST API wrapper.

Handles token lifecycle (acquire, refresh, revoke) and provides
typed methods for the Clio Manage API v4.
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# Clio API v4 base
CLIO_API_V4 = f"{settings.clio_api_base_url}/api/v4"


# ─── OAuth2 helpers ──────────────────────────────────────────────────────────


def build_authorize_url(state: str) -> str:
    """Build the Clio OAuth2 authorization URL."""
    params = {
        "response_type": "code",
        "client_id": settings.clio_client_id,
        "redirect_uri": settings.clio_redirect_uri
        or (f"{settings.backend_url}/api/v1/integrations/clio/callback"),
        "state": state,
    }
    return f"{settings.clio_auth_url}?{urlencode(params)}"


def generate_state() -> str:
    """Generate a random OAuth state parameter."""
    return secrets.token_urlsafe(32)


async def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Exchange an authorization code for access/refresh tokens."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                settings.clio_token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.clio_client_id,
                    "client_secret": settings.clio_client_secret,
                    "redirect_uri": settings.clio_redirect_uri
                    or (f"{settings.backend_url}/api/v1/integrations/clio/callback"),
                },
            )
            resp.raise_for_status()
            return dict(resp.json())
        except httpx.HTTPStatusError as e:
            logger.error("clio_token_exchange_failed", extra={"status": e.response.status_code})
            raise ValidationError(detail="Failed to connect to Clio. Please try again.") from e
        except httpx.HTTPError as e:
            logger.error("clio_token_exchange_error", exc_info=True)
            raise ValidationError(detail="Failed to connect to Clio. Please try again.") from e


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """Refresh an expired access token."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                settings.clio_token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": settings.clio_client_id,
                    "client_secret": settings.clio_client_secret,
                },
            )
            resp.raise_for_status()
            return dict(resp.json())
        except httpx.HTTPError as e:
            logger.error("clio_token_refresh_failed", exc_info=True)
            raise ValidationError(detail="Failed to refresh Clio connection.") from e


async def revoke_token(access_token: str) -> None:
    """Revoke an access token (best-effort)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(
                f"{settings.clio_api_base_url}/oauth/deauthorize",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except httpx.HTTPError:
            logger.warning("clio_token_revoke_failed", exc_info=True)


def token_expires_at(expires_in: int | None) -> datetime:
    """Calculate token expiration from expires_in seconds."""
    return datetime.now(UTC) + timedelta(seconds=(expires_in or 3600))


# ─── Clio API wrapper ────────────────────────────────────────────────────────


class ClioAPI:
    """Thin async wrapper around the Clio Manage API v4."""

    def __init__(self, access_token: str) -> None:
        self._token = access_token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{CLIO_API_V4}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(method, url, headers=self._headers(), **kwargs)
            resp.raise_for_status()
            if resp.status_code == 204:
                return {}
            return dict(resp.json())

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("POST", path, json=json)

    async def _patch(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("PATCH", path, json=json)

    # ── Account ───────────────────────────────────────────────────────────

    async def get_account(self) -> dict[str, Any]:
        """Get the current Clio account info."""
        return await self._get("/users/who_am_i", params={"fields": "id,name,account"})

    # ── Matters ───────────────────────────────────────────────────────────

    async def list_matters(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        updated_since: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "fields": (
                "id,display_number,description,status,"
                "practice_area,client,open_date,close_date,custom_field_values"
            ),
            "limit": limit,
            "offset": offset,
            "order": "id(asc)",
        }
        if updated_since:
            params["updated_since"] = updated_since
        return await self._get("/matters", params=params)

    async def get_matter(self, matter_id: int) -> dict[str, Any]:
        return await self._get(
            f"/matters/{matter_id}",
            params={
                "fields": (
                    "id,display_number,description,status,practice_area,client,open_date,close_date"
                ),
            },
        )

    async def create_matter(self, data: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/matters", json={"data": data})

    async def update_matter(self, matter_id: int, data: dict[str, Any]) -> dict[str, Any]:
        return await self._patch(f"/matters/{matter_id}", json={"data": data})

    # ── Activities (Time Entries) ─────────────────────────────────────────

    async def list_activities(
        self,
        *,
        matter_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
        updated_since: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "fields": "id,type,date,quantity,note,matter,user",
            "limit": limit,
            "offset": offset,
        }
        if matter_id:
            params["matter_id"] = matter_id
        if updated_since:
            params["updated_since"] = updated_since
        return await self._get("/activities", params=params)

    async def create_activity(self, data: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/activities", json={"data": data})

    # ── Contacts ──────────────────────────────────────────────────────────

    async def list_contacts(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        updated_since: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "fields": "id,name,first_name,last_name,type,email_addresses,phone_numbers,company",
            "limit": limit,
            "offset": offset,
        }
        if updated_since:
            params["updated_since"] = updated_since
        return await self._get("/contacts", params=params)

    async def create_contact(self, data: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/contacts", json={"data": data})

    async def update_contact(self, contact_id: int, data: dict[str, Any]) -> dict[str, Any]:
        return await self._patch(f"/contacts/{contact_id}", json={"data": data})

    # ── Webhooks ──────────────────────────────────────────────────────────

    async def list_webhooks(self) -> dict[str, Any]:
        return await self._get("/webhooks")

    async def create_webhook(self, url: str, events: list[str]) -> dict[str, Any]:
        return await self._post(
            "/webhooks",
            json={"data": {"url": url, "events": events}},
        )
