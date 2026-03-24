"""Clio sync service — bidirectional sync for matters, time entries, and contacts.

Manages the IntegrationConnection lifecycle and sync operations.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy import select

from app.core.events import event_logger
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.enums import (
    ActorType,
    IntegrationProvider,
    IntegrationStatus,
    MatterStatus,
    SyncStatus,
)
from app.models.integration_connections import IntegrationConnection
from app.models.matters import Matter
from app.models.stakeholders import Stakeholder
from app.models.time_entries import TimeEntry
from app.services.clio_client import (
    ClioAPI,
    build_authorize_url,
    exchange_code_for_tokens,
    generate_state,
    refresh_access_token,
    revoke_token,
    token_expires_at,
)

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)


# ─── Connection management ───────────────────────────────────────────────────


async def get_connection(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    provider: str = "clio",
) -> IntegrationConnection | None:
    """Get an integration connection for a firm/provider."""
    result = await db.execute(
        select(IntegrationConnection).where(
            IntegrationConnection.firm_id == firm_id,
            IntegrationConnection.provider == provider,
        )
    )
    return result.scalar_one_or_none()


async def get_connection_or_404(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    provider: str = "clio",
) -> IntegrationConnection:
    conn = await get_connection(db, firm_id=firm_id, provider=provider)
    if conn is None:
        raise NotFoundError(detail=f"{provider.title()} integration not connected")
    return conn


async def initiate_oauth(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
) -> dict[str, str]:
    """Start the Clio OAuth2 flow. Returns authorize URL and state."""
    state = generate_state()

    # Store state in a pending connection
    conn = await get_connection(db, firm_id=firm_id, provider="clio")
    if conn and conn.status == IntegrationStatus.connected:
        raise ConflictError(detail="Clio is already connected. Disconnect first to reconnect.")

    if conn is None:
        conn = IntegrationConnection(
            firm_id=firm_id,
            provider=IntegrationProvider.clio,
            status=IntegrationStatus.pending,
            connected_by=current_user.user_id,
        )
        db.add(conn)

    conn.status = IntegrationStatus.pending
    conn.settings = {**conn.settings, "oauth_state": state}
    conn.connected_by = current_user.user_id
    await db.flush()

    authorize_url = build_authorize_url(state)
    return {"authorize_url": authorize_url, "state": state}


async def complete_oauth(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    code: str,
    state: str,
) -> IntegrationConnection:
    """Complete the OAuth2 flow with the authorization code."""
    conn = await get_connection(db, firm_id=firm_id, provider="clio")
    if conn is None:
        raise NotFoundError(detail="No pending Clio connection found")

    stored_state = conn.settings.get("oauth_state")
    if not stored_state or stored_state != state:
        raise ValidationError(detail="Invalid OAuth state parameter")

    # Immediately invalidate state to prevent reuse
    new_settings = {k: v for k, v in conn.settings.items() if k != "oauth_state"}
    conn.settings = new_settings
    await db.flush()

    # Exchange code for tokens
    token_data = await exchange_code_for_tokens(code)

    conn.access_token = token_data.get("access_token")
    conn.refresh_token = token_data.get("refresh_token")
    conn.token_expires_at = token_expires_at(token_data.get("expires_in"))

    # Validate connection by fetching account info before marking connected
    try:
        api = ClioAPI(str(conn.access_token))
        account_info = await api.get_account()
        user_data = account_info.get("data", {})
        account = user_data.get("account", {})
        conn.external_account_id = str(account.get("id", ""))
        conn.external_account_name = account.get("name", user_data.get("name", ""))
        conn.status = IntegrationStatus.connected
    except httpx.HTTPError:
        logger.error("clio_account_fetch_failed", exc_info=True)
        conn.status = IntegrationStatus.error
        conn.last_sync_error = "Connected but failed to verify Clio account"

    await db.flush()

    await event_logger.log(
        db,
        matter_id=firm_id,
        actor_id=conn.connected_by,
        actor_type=ActorType.user,
        entity_type="integration",
        entity_id=conn.id,
        action="connected",
        metadata={"provider": "clio", "account": conn.external_account_name},
    )

    return conn


async def disconnect(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
) -> None:
    """Disconnect the Clio integration and revoke tokens."""
    conn = await get_connection_or_404(db, firm_id=firm_id, provider="clio")

    # Best-effort token revocation
    if conn.access_token:
        await revoke_token(conn.access_token)

    conn.status = IntegrationStatus.disconnected
    conn.access_token = None
    conn.refresh_token = None
    conn.token_expires_at = None
    conn.disconnected_at = datetime.now(UTC)
    conn.last_sync_error = None
    await db.flush()

    await event_logger.log(
        db,
        matter_id=firm_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="integration",
        entity_id=conn.id,
        action="disconnected",
        metadata={"provider": "clio"},
    )


async def update_settings(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    updates: dict[str, Any],
) -> IntegrationConnection:
    """Update integration settings."""
    conn = await get_connection_or_404(db, firm_id=firm_id, provider="clio")
    new_settings = {**conn.settings}
    for key, value in updates.items():
        if value is not None:
            new_settings[key] = value
    conn.settings = new_settings
    await db.flush()
    return conn


# ─── Token management ────────────────────────────────────────────────────────


async def _ensure_valid_token(
    db: AsyncSession,
    conn: IntegrationConnection,
) -> str:
    """Ensure the access token is valid, refreshing if needed."""
    if conn.access_token is None or conn.refresh_token is None:
        raise ValidationError(detail="Clio is not connected. Please reconnect.")

    if conn.token_expires_at and conn.token_expires_at <= datetime.now(UTC):
        token_data = await refresh_access_token(conn.refresh_token)
        conn.access_token = token_data.get("access_token")
        conn.refresh_token = token_data.get("refresh_token", conn.refresh_token)
        conn.token_expires_at = token_expires_at(token_data.get("expires_in"))
        await db.flush()

    return conn.access_token  # type: ignore[return-value]


# ─── Sync: Matters (bidirectional) ───────────────────────────────────────────


async def sync_matters(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
    direction: str = "bidirectional",
) -> dict[str, Any]:
    """Sync matters between Estate Executor and Clio."""
    conn = await get_connection_or_404(db, firm_id=firm_id, provider="clio")
    token = await _ensure_valid_token(db, conn)
    api = ClioAPI(token)

    conn.last_sync_status = SyncStatus.syncing
    await db.flush()

    result: dict[str, Any] = {
        "resource": "matters",
        "direction": direction,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
    }
    entity_map = dict(conn.entity_map) if conn.entity_map else {}
    matter_map = entity_map.get("matters", {})

    try:
        # Pull from Clio
        if direction in ("pull", "bidirectional"):
            updated_since = conn.sync_cursor
            clio_resp = await api.list_matters(updated_since=updated_since)
            clio_matters = clio_resp.get("data", [])
            for clio_matter in clio_matters:
                try:
                    clio_id = str(clio_matter.get("id", ""))
                    if not clio_id:
                        continue
                    our_id = matter_map.get(f"clio:{clio_id}")

                    if our_id:
                        matter_result = await db.execute(select(Matter).where(Matter.id == our_id))
                        matter = matter_result.scalar_one_or_none()
                        if matter:
                            matter.title = clio_matter.get("description", matter.title)
                            result["updated"] += 1
                    else:
                        result["skipped"] += 1
                except (KeyError, ValueError, httpx.HTTPError) as e:
                    result["errors"].append(f"Pull matter {clio_matter.get('id')}: {e}")

            # Update sync cursor for incremental sync next time
            if clio_matters:
                conn.sync_cursor = datetime.now(UTC).isoformat()

        # Push to Clio
        if direction in ("push", "bidirectional"):
            matters_q = select(Matter).where(
                Matter.firm_id == firm_id,
                Matter.status == MatterStatus.active,
            )
            our_matters = list((await db.execute(matters_q)).scalars().all())

            for matter in our_matters:
                our_id = str(matter.id)
                clio_id = matter_map.get(f"local:{our_id}")

                try:
                    if clio_id:
                        # Update in Clio
                        await api.update_matter(
                            int(clio_id),
                            {"description": matter.title},
                        )
                        result["updated"] += 1
                    else:
                        # Create in Clio
                        clio_data = {
                            "description": matter.title,
                            "status": "Open" if matter.status == MatterStatus.active else "Closed",
                        }
                        resp = await api.create_matter(clio_data)
                        new_clio_id = str(resp.get("data", {}).get("id", ""))
                        if new_clio_id:
                            matter_map[f"local:{our_id}"] = new_clio_id
                            matter_map[f"clio:{new_clio_id}"] = our_id
                            result["created"] += 1
                except httpx.HTTPError as e:
                    result["errors"].append(f"Push matter {matter.title}: {e}")

        entity_map["matters"] = matter_map
        conn.entity_map = entity_map
        conn.last_sync_at = datetime.now(UTC)
        conn.last_sync_status = SyncStatus.success
        conn.last_sync_error = None
        await db.flush()

    except Exception as e:
        conn.last_sync_status = SyncStatus.failed
        conn.last_sync_error = str(e)
        await db.flush()
        result["errors"].append(str(e))

    result["synced_at"] = datetime.now(UTC)

    await event_logger.log(
        db,
        matter_id=firm_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="integration",
        entity_id=conn.id,
        action="sync_matters",
        metadata={
            "created": result["created"],
            "updated": result["updated"],
            "errors": len(result["errors"]),
        },
    )

    return result


# ─── Sync: Time Entries (push to Clio) ───────────────────────────────────────


async def sync_time_entries(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
    matter_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Push time entries from Estate Executor to Clio activities."""
    conn = await get_connection_or_404(db, firm_id=firm_id, provider="clio")
    token = await _ensure_valid_token(db, conn)
    api = ClioAPI(token)

    result: dict[str, Any] = {
        "resource": "time_entries",
        "direction": "push",
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
    }
    entity_map = dict(conn.entity_map) if conn.entity_map else {}
    time_map = entity_map.get("time_entries", {})
    matter_map = entity_map.get("matters", {})

    # Query time entries
    filters: list[Any] = []
    if matter_id:
        filters.append(TimeEntry.matter_id == matter_id)
    else:
        # Get all matters for this firm
        matter_ids_q = select(Matter.id).where(Matter.firm_id == firm_id)
        matter_ids = [r[0] for r in (await db.execute(matter_ids_q)).all()]
        if not matter_ids:
            return result
        filters.append(TimeEntry.matter_id.in_(matter_ids))

    entries_q = select(TimeEntry).where(*filters).order_by(TimeEntry.entry_date)
    entries = list((await db.execute(entries_q)).scalars().all())

    for entry in entries:
        entry_key = f"local:{entry.id}"
        if entry_key in time_map:
            result["skipped"] += 1
            continue

        # Need a Clio matter ID
        clio_matter_id = matter_map.get(f"local:{entry.matter_id}")
        if not clio_matter_id:
            result["skipped"] += 1
            continue

        try:
            hours_decimal = entry.hours + (entry.minutes / 60)
            activity_data = {
                "date": entry.entry_date.isoformat(),
                "type": "TimeEntry",
                "quantity": round(hours_decimal, 2),
                "note": entry.description or "",
                "matter": {"id": int(clio_matter_id)},
            }
            resp = await api.create_activity(activity_data)
            clio_activity_id = str(resp.get("data", {}).get("id", ""))
            if clio_activity_id:
                time_map[entry_key] = clio_activity_id
                result["created"] += 1
        except httpx.HTTPError as e:
            result["errors"].append(f"Time entry {entry.id}: {e}")

    entity_map["time_entries"] = time_map
    conn.entity_map = entity_map
    conn.last_sync_at = datetime.now(UTC)
    await db.flush()

    result["synced_at"] = datetime.now(UTC)
    return result


# ─── Sync: Contacts ↔ Stakeholders ──────────────────────────────────────────


async def sync_contacts(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    current_user: CurrentUser,
    direction: str = "bidirectional",
) -> dict[str, Any]:
    """Sync contacts between Clio contacts and estate stakeholders."""
    conn = await get_connection_or_404(db, firm_id=firm_id, provider="clio")
    token = await _ensure_valid_token(db, conn)
    api = ClioAPI(token)

    result: dict[str, Any] = {
        "resource": "contacts",
        "direction": direction,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
    }
    entity_map = dict(conn.entity_map) if conn.entity_map else {}
    contact_map = entity_map.get("contacts", {})

    try:
        # Pull contacts from Clio — cache for reference, don't auto-create
        if direction in ("pull", "bidirectional"):
            clio_resp = await api.list_contacts()
            for contact in clio_resp.get("data", []):
                clio_id = str(contact.get("id", ""))
                if not clio_id or f"clio:{clio_id}" in contact_map:
                    result["skipped"] += 1
                    continue

                emails = contact.get("email_addresses") or []
                email = emails[0].get("address", "") if isinstance(emails, list) and emails else ""
                if not email:
                    result["skipped"] += 1
                    continue

                # Store as string ID (consistent with other maps)
                # The email is used as the lookup key for matching
                contact_map[f"clio:{clio_id}"] = email
                result["updated"] += 1

        # Push stakeholders to Clio
        if direction in ("push", "bidirectional"):
            matter_ids_q = select(Matter.id).where(Matter.firm_id == firm_id)
            matter_ids = [r[0] for r in (await db.execute(matter_ids_q)).all()]

            if matter_ids:
                stakeholders_q = (
                    select(Stakeholder)
                    .where(Stakeholder.matter_id.in_(matter_ids))
                    .order_by(Stakeholder.email, Stakeholder.created_at)
                    .distinct(Stakeholder.email)
                )
                stakeholders = list((await db.execute(stakeholders_q)).scalars().all())

                for sh in stakeholders:
                    sh_key = f"local:{sh.id}"
                    if sh_key in contact_map:
                        result["skipped"] += 1
                        continue

                    try:
                        names = sh.full_name.split(" ", 1)
                        contact_data: dict[str, Any] = {
                            "first_name": names[0],
                            "last_name": names[1] if len(names) > 1 else "",
                            "type": "Person",
                            "email_addresses": [
                                {"name": "Work", "address": sh.email, "default_email": True}
                            ],
                        }
                        resp = await api.create_contact(contact_data)
                        new_clio_id = str(resp.get("data", {}).get("id", ""))
                        if new_clio_id:
                            contact_map[sh_key] = new_clio_id
                            contact_map[f"clio:{new_clio_id}"] = str(sh.id)
                            result["created"] += 1
                    except httpx.HTTPError as e:
                        result["errors"].append(f"Contact {sh.email}: {e}")

        entity_map["contacts"] = contact_map
        conn.entity_map = entity_map
        conn.last_sync_at = datetime.now(UTC)
        await db.flush()

    except Exception as e:
        result["errors"].append(str(e))

    result["synced_at"] = datetime.now(UTC)
    return result


# ─── Webhook handling ────────────────────────────────────────────────────────


async def handle_clio_webhook(
    db: AsyncSession,
    *,
    payload: dict[str, Any],
) -> None:
    """Handle inbound Clio webhook events."""
    event_type = payload.get("type", "")
    data = payload.get("data", {})
    subject = data.get("subject", {})

    logger.info("clio_webhook_received", extra={"type": event_type})

    if event_type == "matter.updated":
        await _handle_matter_updated(db, subject)
    elif event_type == "matter.created":
        logger.info("clio_webhook_matter_created", extra={"clio_id": subject.get("id")})
    elif event_type == "contact.updated":
        logger.info("clio_webhook_contact_updated", extra={"clio_id": subject.get("id")})
    else:
        logger.debug("clio_webhook_unhandled", extra={"type": event_type})


async def _handle_matter_updated(
    db: AsyncSession,
    subject: dict[str, Any],
) -> None:
    """Handle a Clio matter.updated webhook — update linked local matter."""
    clio_id = str(subject.get("id", ""))
    if not clio_id:
        return

    # Find any connection that maps this Clio matter
    result = await db.execute(
        select(IntegrationConnection).where(
            IntegrationConnection.provider == IntegrationProvider.clio,
            IntegrationConnection.status == IntegrationStatus.connected,
        )
    )
    connections = list(result.scalars().all())

    for conn in connections:
        matter_map = (conn.entity_map or {}).get("matters", {})
        local_id = matter_map.get(f"clio:{clio_id}")
        if local_id:
            matter_result = await db.execute(select(Matter).where(Matter.id == local_id))
            matter = matter_result.scalar_one_or_none()
            if matter and subject.get("description"):
                matter.title = subject["description"]
                await db.flush()
                logger.info(
                    "clio_webhook_matter_synced",
                    extra={"clio_id": clio_id, "local_id": str(local_id)},
                )
            break
