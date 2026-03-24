"""Webhook service — CRUD, delivery, test, logs."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy import func, select

from app.core.exceptions import NotFoundError, ValidationError
from app.models.webhooks import Webhook, WebhookDelivery

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

# Supported webhook event types
SUPPORTED_EVENTS = [
    "matter.created",
    "matter.updated",
    "matter.closed",
    "task.created",
    "task.updated",
    "task.completed",
    "document.uploaded",
    "document.updated",
    "stakeholder.added",
    "stakeholder.removed",
    "asset.created",
    "asset.updated",
    "distribution.created",
    "distribution.updated",
    "communication.created",
    "deadline.approaching",
    "deadline.missed",
]

MAX_WEBHOOKS_PER_FIRM = 10
DELIVERY_TIMEOUT_SECONDS = 10.0
MAX_RESPONSE_BODY_LEN = 2048


def _generate_secret() -> str:
    return f"whsec_{secrets.token_hex(24)}"


def _sign_payload(secret: str, payload: str) -> str:
    """HMAC-SHA256 signature of the payload."""
    return hmac.new(
        secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()


# ─── CRUD ────────────────────────────────────────────────────────────────────


async def list_webhooks(
    db: AsyncSession, *, firm_id: uuid.UUID
) -> list[Webhook]:
    result = await db.execute(
        select(Webhook)
        .where(Webhook.firm_id == firm_id)
        .order_by(Webhook.created_at.desc())
    )
    return list(result.scalars().all())


async def create_webhook(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    url: str,
    events: list[str],
    description: str | None = None,
    current_user: CurrentUser,
) -> Webhook:
    # Validate events
    invalid = [e for e in events if e not in SUPPORTED_EVENTS]
    if invalid:
        raise ValidationError(
            detail=f"Unsupported events: {', '.join(invalid)}"
        )

    # Check per-firm limit
    count_result = await db.execute(
        select(func.count()).where(Webhook.firm_id == firm_id)
    )
    count = count_result.scalar() or 0
    if count >= MAX_WEBHOOKS_PER_FIRM:
        raise ValidationError(
            detail=f"Maximum {MAX_WEBHOOKS_PER_FIRM} webhooks per firm"
        )

    webhook = Webhook(
        firm_id=firm_id,
        url=url,
        description=description,
        secret=_generate_secret(),
        events=events,
        created_by=current_user.user_id,
    )
    db.add(webhook)
    await db.flush()
    return webhook


async def get_webhook(
    db: AsyncSession, *, webhook_id: uuid.UUID, firm_id: uuid.UUID
) -> Webhook:
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.firm_id == firm_id
        )
    )
    webhook = result.scalar_one_or_none()
    if webhook is None:
        raise NotFoundError(detail="Webhook not found")
    return webhook


async def update_webhook(
    db: AsyncSession,
    *,
    webhook_id: uuid.UUID,
    firm_id: uuid.UUID,
    updates: dict[str, Any],
) -> Webhook:
    webhook = await get_webhook(db, webhook_id=webhook_id, firm_id=firm_id)

    if "events" in updates:
        invalid = [
            e for e in updates["events"] if e not in SUPPORTED_EVENTS
        ]
        if invalid:
            raise ValidationError(
                detail=f"Unsupported events: {', '.join(invalid)}"
            )

    for key, value in updates.items():
        if value is not None and hasattr(webhook, key) and key != "secret":
            setattr(webhook, key, value)

    await db.flush()
    return webhook


async def delete_webhook(
    db: AsyncSession, *, webhook_id: uuid.UUID, firm_id: uuid.UUID
) -> None:
    webhook = await get_webhook(db, webhook_id=webhook_id, firm_id=firm_id)
    await db.delete(webhook)
    await db.flush()


async def rotate_secret(
    db: AsyncSession, *, webhook_id: uuid.UUID, firm_id: uuid.UUID
) -> Webhook:
    webhook = await get_webhook(db, webhook_id=webhook_id, firm_id=firm_id)
    webhook.secret = _generate_secret()
    await db.flush()
    return webhook


# ─── Delivery ────────────────────────────────────────────────────────────────


async def deliver_webhook(
    db: AsyncSession,
    *,
    webhook: Webhook,
    event_type: str,
    payload: dict[str, Any],
) -> WebhookDelivery:
    """Deliver a webhook to the configured URL with HMAC signature."""
    payload_str = json.dumps(payload, default=str, sort_keys=True)
    signature = _sign_payload(webhook.secret, payload_str)
    timestamp = str(int(time.time()))

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": event_type,
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Webhook-Timestamp": timestamp,
        "X-Webhook-ID": str(webhook.id),
        "User-Agent": "EstateExecutor-Webhook/1.0",
    }

    delivery = WebhookDelivery(
        webhook_id=webhook.id,
        event_type=event_type,
        payload=payload,
    )

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(
            timeout=DELIVERY_TIMEOUT_SECONDS
        ) as client:
            resp = await client.post(
                webhook.url, content=payload_str, headers=headers
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)

            delivery.status_code = resp.status_code
            delivery.response_body = resp.text[:MAX_RESPONSE_BODY_LEN]
            delivery.duration_ms = elapsed_ms
            delivery.success = 200 <= resp.status_code < 300

            if delivery.success:
                webhook.failure_count = 0
            else:
                webhook.failure_count += 1

    except httpx.TimeoutException:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        delivery.error_message = "Request timed out"
        delivery.duration_ms = elapsed_ms
        delivery.success = False
        webhook.failure_count += 1

    except httpx.HTTPError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        delivery.error_message = str(exc)[:MAX_RESPONSE_BODY_LEN]
        delivery.duration_ms = elapsed_ms
        delivery.success = False
        webhook.failure_count += 1

    webhook.last_triggered_at = datetime.now(UTC)
    db.add(delivery)
    await db.flush()

    logger.info(
        "webhook_delivered",
        extra={
            "webhook_id": str(webhook.id),
            "event": event_type,
            "success": delivery.success,
            "status_code": delivery.status_code,
            "duration_ms": delivery.duration_ms,
        },
    )

    return delivery


async def dispatch_event(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any],
) -> list[WebhookDelivery]:
    """Dispatch an event to all matching active webhooks for a firm."""
    result = await db.execute(
        select(Webhook).where(
            Webhook.firm_id == firm_id,
            Webhook.is_active.is_(True),
        )
    )
    webhooks = list(result.scalars().all())

    deliveries: list[WebhookDelivery] = []
    for wh in webhooks:
        if event_type in (wh.events or []):
            delivery = await deliver_webhook(
                db, webhook=wh, event_type=event_type, payload=payload
            )
            deliveries.append(delivery)

    return deliveries


async def test_webhook(
    db: AsyncSession, *, webhook_id: uuid.UUID, firm_id: uuid.UUID
) -> WebhookDelivery:
    """Send a test ping event to the webhook endpoint."""
    webhook = await get_webhook(db, webhook_id=webhook_id, firm_id=firm_id)
    test_payload = {
        "event": "webhook.test",
        "webhook_id": str(webhook.id),
        "firm_id": str(firm_id),
        "timestamp": datetime.now(UTC).isoformat(),
        "message": "This is a test webhook delivery from Estate Executor.",
    }
    return await deliver_webhook(
        db, webhook=webhook, event_type="webhook.test", payload=test_payload
    )


# ─── Delivery logs ───────────────────────────────────────────────────────────


async def list_deliveries(
    db: AsyncSession,
    *,
    webhook_id: uuid.UUID,
    firm_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[WebhookDelivery]:
    """List delivery logs for a webhook, newest first."""
    # Verify ownership
    await get_webhook(db, webhook_id=webhook_id, firm_id=firm_id)

    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


def get_supported_events() -> list[str]:
    """Return the list of subscribable event types."""
    return SUPPORTED_EVENTS.copy()
