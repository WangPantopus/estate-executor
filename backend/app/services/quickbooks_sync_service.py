"""QuickBooks sync service — distributions, transactions, account balances."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy import select

from app.core.events import event_logger
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.assets import Asset
from app.models.distributions import Distribution
from app.models.enums import (
    ActorType,
    AssetType,
    IntegrationProvider,
    IntegrationStatus,
)
from app.models.integration_connections import IntegrationConnection
from app.models.matters import Matter
from app.services.quickbooks_client import (
    QuickBooksAPI,
    build_authorize_url,
    exchange_code_for_tokens,
    generate_state,
    refresh_access_token,
    token_expires_at,
)

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

# Bank account asset types that map to QBO bank accounts
_BANK_ASSET_TYPES = {AssetType.bank_account, AssetType.brokerage_account}


# ─── Connection management ───────────────────────────────────────────────────


async def get_connection(db: AsyncSession, *, firm_id: uuid.UUID) -> IntegrationConnection | None:
    result = await db.execute(
        select(IntegrationConnection).where(
            IntegrationConnection.firm_id == firm_id,
            IntegrationConnection.provider == IntegrationProvider.quickbooks,
        )
    )
    return result.scalar_one_or_none()


async def get_connection_or_404(db: AsyncSession, *, firm_id: uuid.UUID) -> IntegrationConnection:
    conn = await get_connection(db, firm_id=firm_id)
    if conn is None:
        raise NotFoundError(detail="QuickBooks integration not connected")
    return conn


async def initiate_oauth(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
) -> dict[str, str]:
    state = generate_state()

    conn = await get_connection(db, firm_id=firm_id)
    if conn and conn.status == IntegrationStatus.connected:
        raise ConflictError(detail="QuickBooks is already connected. Disconnect first.")

    if conn is None:
        conn = IntegrationConnection(
            firm_id=firm_id,
            provider=IntegrationProvider.quickbooks,
            status=IntegrationStatus.pending,
            connected_by=current_user.user_id,
        )
        db.add(conn)

    conn.status = IntegrationStatus.pending
    conn.settings = {**conn.settings, "oauth_state": state}
    conn.connected_by = current_user.user_id
    await db.flush()

    return {"authorize_url": build_authorize_url(state), "state": state}


async def complete_oauth(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    code: str,
    state: str,
    realm_id: str,
) -> IntegrationConnection:
    conn = await get_connection(db, firm_id=firm_id)
    if conn is None:
        raise NotFoundError(detail="No pending QuickBooks connection")

    stored_state = conn.settings.get("oauth_state")
    if not stored_state or stored_state != state:
        raise ValidationError(detail="Invalid OAuth state parameter")

    # Invalidate state immediately
    new_settings = {k: v for k, v in conn.settings.items() if k != "oauth_state"}
    conn.settings = new_settings
    await db.flush()

    token_data = await exchange_code_for_tokens(code, realm_id)
    conn.access_token = token_data.get("access_token")
    conn.refresh_token = token_data.get("refresh_token")
    conn.token_expires_at = token_expires_at(token_data.get("expires_in"))
    conn.external_account_id = realm_id

    # Validate by fetching company info
    try:
        api = QuickBooksAPI(str(conn.access_token), realm_id)
        info = await api.get_company_info()
        company = info.get("CompanyInfo", {})
        conn.external_account_name = company.get("CompanyName", "")
        conn.status = IntegrationStatus.connected
    except httpx.HTTPError:
        logger.error("qbo_company_info_failed", exc_info=True)
        conn.status = IntegrationStatus.error
        conn.last_sync_error = "Failed to verify QuickBooks account"

    await db.flush()

    await event_logger.log(
        db,
        matter_id=firm_id,
        actor_id=conn.connected_by,
        actor_type=ActorType.user,
        entity_type="integration",
        entity_id=conn.id,
        action="connected",
        metadata={"provider": "quickbooks", "company": conn.external_account_name},
    )
    return conn


async def disconnect(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
) -> None:
    conn = await get_connection_or_404(db, firm_id=firm_id)
    conn.status = IntegrationStatus.disconnected
    conn.access_token = None
    conn.refresh_token = None
    conn.token_expires_at = None
    conn.disconnected_at = datetime.now(UTC)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=firm_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="integration",
        entity_id=conn.id,
        action="disconnected",
        metadata={"provider": "quickbooks"},
    )


# ─── Token management ────────────────────────────────────────────────────────


async def _ensure_valid_token(db: AsyncSession, conn: IntegrationConnection) -> QuickBooksAPI:
    if not conn.access_token or not conn.refresh_token:
        raise ValidationError(detail="QuickBooks not connected.")

    if conn.token_expires_at and conn.token_expires_at <= datetime.now(UTC):
        token_data = await refresh_access_token(conn.refresh_token)
        conn.access_token = token_data.get("access_token")
        conn.refresh_token = token_data.get("refresh_token", conn.refresh_token)
        conn.token_expires_at = token_expires_at(token_data.get("expires_in"))
        await db.flush()

    realm_id = conn.external_account_id or ""
    return QuickBooksAPI(str(conn.access_token), realm_id)


# ─── Push: Distributions → Journal Entries ───────────────────────────────────


async def push_distributions(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
    matter_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Push estate distributions as journal entries to QuickBooks."""
    conn = await get_connection_or_404(db, firm_id=firm_id)
    api = await _ensure_valid_token(db, conn)

    result: dict[str, Any] = {
        "resource": "distributions",
        "direction": "push",
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
    }
    entity_map = dict(conn.entity_map) if conn.entity_map else {}
    je_map = entity_map.get("journal_entries", {})

    # Get distributions
    filters: list[Any] = []
    if matter_id:
        filters.append(Distribution.matter_id == matter_id)
    else:
        matter_ids_q = select(Matter.id).where(Matter.firm_id == firm_id)
        matter_ids = [r[0] for r in (await db.execute(matter_ids_q)).all()]
        if not matter_ids:
            return result
        filters.append(Distribution.matter_id.in_(matter_ids))

    dists_q = select(Distribution).where(*filters).order_by(Distribution.distribution_date)
    distributions = list((await db.execute(dists_q)).scalars().all())

    for dist in distributions:
        dist_key = f"local:{dist.id}"
        if dist_key in je_map:
            result["skipped"] += 1
            continue

        if dist.amount is None or dist.amount <= 0:
            result["skipped"] += 1
            continue

        try:
            # Build journal entry: debit Estate Distribution, credit Estate Bank
            je_data = {
                "TxnDate": dist.distribution_date.isoformat(),
                "DocNumber": f"DIST-{str(dist.id)[:8]}",
                "PrivateNote": (f"Estate distribution: {dist.description}"),
                "Line": [
                    {
                        "Amount": float(dist.amount),
                        "DetailType": "JournalEntryLineDetail",
                        "Description": dist.description,
                        "JournalEntryLineDetail": {
                            "PostingType": "Debit",
                            "AccountRef": {
                                "name": "Estate Distributions",
                            },
                        },
                    },
                    {
                        "Amount": float(dist.amount),
                        "DetailType": "JournalEntryLineDetail",
                        "Description": dist.description,
                        "JournalEntryLineDetail": {
                            "PostingType": "Credit",
                            "AccountRef": {
                                "name": "Estate Bank Account",
                            },
                        },
                    },
                ],
            }

            resp = await api.create_journal_entry(je_data)
            qb_je = resp.get("JournalEntry", {})
            qb_id = str(qb_je.get("Id", ""))
            if qb_id:
                je_map[dist_key] = qb_id
                result["created"] += 1
        except httpx.HTTPError as e:
            result["errors"].append(f"Distribution {dist.id}: {e}")

    entity_map["journal_entries"] = je_map
    conn.entity_map = entity_map
    conn.last_sync_at = datetime.now(UTC)
    await db.flush()

    result["synced_at"] = datetime.now(UTC)

    await event_logger.log(
        db,
        matter_id=firm_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="integration",
        entity_id=conn.id,
        action="sync_distributions",
        metadata={
            "created": result["created"],
            "errors": len(result["errors"]),
        },
    )
    return result


# ─── Push: Bank Transactions → QB Purchases ──────────────────────────────────


async def push_transactions(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
    matter_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Push estate bank-related assets as QBO purchases/deposits.

    This creates a record of the estate's bank account activity in QB.
    Assets of type bank_account/brokerage_account with values are synced.
    """
    conn = await get_connection_or_404(db, firm_id=firm_id)
    api = await _ensure_valid_token(db, conn)

    result: dict[str, Any] = {
        "resource": "transactions",
        "direction": "push",
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
    }
    entity_map = dict(conn.entity_map) if conn.entity_map else {}
    txn_map = entity_map.get("transactions", {})

    # Get bank-type assets
    filters: list[Any] = [Asset.asset_type.in_([t.value for t in _BANK_ASSET_TYPES])]
    if matter_id:
        filters.append(Asset.matter_id == matter_id)
    else:
        matter_ids_q = select(Matter.id).where(Matter.firm_id == firm_id)
        matter_ids = [r[0] for r in (await db.execute(matter_ids_q)).all()]
        if not matter_ids:
            return result
        filters.append(Asset.matter_id.in_(matter_ids))

    assets_q = select(Asset).where(*filters)
    assets = list((await db.execute(assets_q)).scalars().all())

    for asset in assets:
        asset_key = f"local:{asset.id}"
        if asset_key in txn_map:
            result["skipped"] += 1
            continue

        value = asset.current_estimated_value or asset.date_of_death_value
        if not value or value <= 0:
            result["skipped"] += 1
            continue

        try:
            # Create as a deposit to record the estate asset
            deposit_data = {
                "TxnDate": datetime.now(UTC).date().isoformat(),
                "PrivateNote": (
                    f"Estate asset: {asset.title} ({asset.institution or 'Unknown institution'})"
                ),
                "DepositToAccountRef": {
                    "name": "Estate Bank Account",
                },
                "Line": [
                    {
                        "Amount": float(value),
                        "DetailType": "DepositLineDetail",
                        "Description": asset.title,
                        "DepositLineDetail": {
                            "AccountRef": {
                                "name": "Estate Assets",
                            },
                        },
                    }
                ],
            }

            resp = await api.create_deposit(deposit_data)
            qb_dep = resp.get("Deposit", {})
            qb_id = str(qb_dep.get("Id", ""))
            if qb_id:
                txn_map[asset_key] = qb_id
                result["created"] += 1
        except httpx.HTTPError as e:
            result["errors"].append(f"Asset {asset.title}: {e}")

    entity_map["transactions"] = txn_map
    conn.entity_map = entity_map
    conn.last_sync_at = datetime.now(UTC)
    await db.flush()

    result["synced_at"] = datetime.now(UTC)
    return result


# ─── Pull: Bank Account Balances ─────────────────────────────────────────────


async def pull_account_balances(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Pull bank account balances from QBO for reconciliation."""
    conn = await get_connection_or_404(db, firm_id=firm_id)
    api = await _ensure_valid_token(db, conn)

    result: dict[str, Any] = {
        "resource": "account_balances",
        "direction": "pull",
        "accounts": [],
        "errors": [],
    }

    try:
        # Query all Bank type accounts
        bank_resp = await api.query_accounts(account_type="Bank")
        accounts = bank_resp.get("QueryResponse", {}).get("Account", [])

        for acct in accounts:
            result["accounts"].append(
                {
                    "qbo_id": acct.get("Id"),
                    "name": acct.get("Name", ""),
                    "account_type": acct.get("AccountType", ""),
                    "account_sub_type": acct.get("AccountSubType", ""),
                    "current_balance": acct.get("CurrentBalance", 0),
                    "currency": acct.get("CurrencyRef", {}).get("value", "USD"),
                    "active": acct.get("Active", True),
                }
            )

        conn.last_sync_at = datetime.now(UTC)
        await db.flush()

    except httpx.HTTPError as e:
        logger.error("qbo_pull_balances_failed", exc_info=True)
        result["errors"].append(str(e))

    result["synced_at"] = datetime.now(UTC)
    return result
