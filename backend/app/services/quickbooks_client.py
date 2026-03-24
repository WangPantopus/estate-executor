"""QuickBooks Online API client — OAuth2 and Accounting API wrapper."""

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


def _api_base() -> str:
    """Return QBO API base URL based on environment."""
    if settings.qbo_environment == "production":
        return "https://quickbooks.api.intuit.com"
    return "https://sandbox-quickbooks.api.intuit.com"


# ─── OAuth2 helpers ──────────────────────────────────────────────────────────


def build_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.qbo_client_id,
        "response_type": "code",
        "scope": "com.intuit.quickbooks.accounting",
        "redirect_uri": settings.qbo_redirect_uri
        or f"{settings.backend_url}/api/v1/integrations/quickbooks/callback",
        "state": state,
    }
    return f"{settings.qbo_auth_url}?{urlencode(params)}"


def generate_state() -> str:
    return secrets.token_urlsafe(32)


async def exchange_code_for_tokens(code: str, realm_id: str) -> dict[str, Any]:
    """Exchange authorization code for tokens. realm_id is the QBO company ID."""
    auth_header = base64.b64encode(
        f"{settings.qbo_client_id}:{settings.qbo_client_secret}".encode()
    ).decode()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                settings.qbo_token_url,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Accept": "application/json",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.qbo_redirect_uri
                    or f"{settings.backend_url}/api/v1/integrations/quickbooks/callback",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            data["realm_id"] = realm_id
            return data
        except httpx.HTTPError as e:
            logger.error("qbo_token_exchange_failed", exc_info=True)
            raise ValidationError(detail="Failed to connect to QuickBooks.") from e


async def refresh_access_token(
    refresh_token: str,
) -> dict[str, Any]:
    auth_header = base64.b64encode(
        f"{settings.qbo_client_id}:{settings.qbo_client_secret}".encode()
    ).decode()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                settings.qbo_token_url,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Accept": "application/json",
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error("qbo_token_refresh_failed", exc_info=True)
            raise ValidationError(detail="Failed to refresh QuickBooks connection.") from e


def token_expires_at(expires_in: int | None) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=(expires_in or 3600))


# ─── QuickBooks Online Accounting API ────────────────────────────────────────


class QuickBooksAPI:
    """Wrapper around QBO Accounting API v3."""

    def __init__(self, access_token: str, realm_id: str) -> None:
        self._token = access_token
        self._realm_id = realm_id
        self._base = f"{_api_base()}/v3/company/{realm_id}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        url = f"{self._base}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method,
                url,
                headers=self._headers(),
                **kwargs,
            )
            resp.raise_for_status()
            if resp.status_code == 204:
                return {}
            return resp.json()

    async def _get(
        self,
        path: str,
        params: dict | None = None,
    ) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, json: dict | None = None) -> dict[str, Any]:
        return await self._request("POST", path, json=json)

    # ── Company Info ──────────────────────────────────────────────────────

    async def get_company_info(self) -> dict[str, Any]:
        return await self._get(f"/companyinfo/{self._realm_id}")

    # ── Journal Entries ───────────────────────────────────────────────────

    async def create_journal_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/journalentry", json=entry)

    async def query_journal_entries(self, where: str = "", limit: int = 100) -> dict[str, Any]:
        query = "SELECT * FROM JournalEntry"
        if where:
            query += f" WHERE {where}"
        query += f" MAXRESULTS {limit}"
        return await self._get("/query", params={"query": query})

    # ── Purchases (bank transactions) ─────────────────────────────────────

    async def create_purchase(self, purchase: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/purchase", json=purchase)

    # ── Accounts ──────────────────────────────────────────────────────────

    _VALID_ACCOUNT_TYPES = frozenset(
        {
            "Bank",
            "Other Current Asset",
            "Fixed Asset",
            "Other Asset",
            "Accounts Receivable",
            "Equity",
            "Expense",
            "Other Expense",
            "Cost of Goods Sold",
            "Accounts Payable",
            "Credit Card",
            "Long Term Liability",
            "Other Current Liability",
            "Income",
            "Other Income",
        }
    )

    async def query_accounts(
        self,
        account_type: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        query = "SELECT * FROM Account"
        if account_type:
            if account_type not in self._VALID_ACCOUNT_TYPES:
                raise ValueError(f"Invalid QBO account type: {account_type}")
            query += f" WHERE AccountType = '{account_type}'"
        query += f" MAXRESULTS {limit}"
        return await self._get("/query", params={"query": query})

    async def get_account(self, account_id: str) -> dict[str, Any]:
        return await self._get(f"/account/{account_id}")

    # ── Deposits ──────────────────────────────────────────────────────────

    async def create_deposit(self, deposit: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/deposit", json=deposit)
