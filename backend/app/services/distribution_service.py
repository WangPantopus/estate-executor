"""Distribution business logic — recording, listing, acknowledgment, summaries."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import selectinload

from app.core.events import event_logger
from app.core.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from app.models.assets import Asset
from app.models.communications import Communication
from app.models.distributions import Distribution
from app.models.enums import (
    ActorType,
    AssetStatus,
    CommunicationType,
    CommunicationVisibility,
    DistributionType,
    StakeholderRole,
)
from app.models.stakeholders import Stakeholder

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_distribution_or_404(
    db: AsyncSession, *, dist_id: uuid.UUID, matter_id: uuid.UUID
) -> Distribution:
    result = await db.execute(
        select(Distribution)
        .options(
            selectinload(Distribution.beneficiary),
            selectinload(Distribution.asset),
        )
        .where(Distribution.id == dist_id, Distribution.matter_id == matter_id)
    )
    dist = result.scalar_one_or_none()
    if dist is None:
        raise NotFoundError(detail="Distribution not found")
    return dist


async def _get_beneficiary_or_404(
    db: AsyncSession, *, stakeholder_id: uuid.UUID, matter_id: uuid.UUID
) -> Stakeholder:
    result = await db.execute(
        select(Stakeholder).where(
            Stakeholder.id == stakeholder_id,
            Stakeholder.matter_id == matter_id,
            Stakeholder.role == StakeholderRole.beneficiary,
        )
    )
    stakeholder = result.scalar_one_or_none()
    if stakeholder is None:
        raise BadRequestError(detail="Beneficiary stakeholder not found on this matter")
    return stakeholder


# ---------------------------------------------------------------------------
# Record distribution
# ---------------------------------------------------------------------------


async def record_distribution(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    asset_id: uuid.UUID | None,
    beneficiary_stakeholder_id: uuid.UUID,
    amount: Decimal | None,
    description: str,
    distribution_type: DistributionType,
    distribution_date: date,
    notes: str | None,
    sender_stakeholder: Stakeholder,
    current_user: CurrentUser,
) -> Distribution:
    """Record a distribution and create associated communication and event."""

    # Validate beneficiary exists and has beneficiary role
    beneficiary = await _get_beneficiary_or_404(
        db, stakeholder_id=beneficiary_stakeholder_id, matter_id=matter_id
    )

    # Validate asset if provided
    asset = None
    if asset_id is not None:
        result = await db.execute(
            select(Asset).where(Asset.id == asset_id, Asset.matter_id == matter_id)
        )
        asset = result.scalar_one_or_none()
        if asset is None:
            raise BadRequestError(detail="Asset not found on this matter")

    # Create distribution record
    dist = Distribution(
        matter_id=matter_id,
        asset_id=asset_id,
        beneficiary_stakeholder_id=beneficiary_stakeholder_id,
        amount=amount,
        description=description,
        distribution_type=distribution_type,
        distribution_date=distribution_date,
        notes=notes,
    )
    db.add(dist)
    await db.flush()

    # Create distribution_notice communication to the beneficiary
    amount_str = f"${amount:,.2f}" if amount is not None else "N/A"
    asset_str = f" from {asset.title}" if asset else ""
    notice_body = (
        f"A distribution has been recorded for you.\n\n"
        f"Description: {description}\n"
        f"Amount: {amount_str}{asset_str}\n"
        f"Type: {distribution_type.value.replace('_', ' ').title()}\n"
        f"Date: {distribution_date.isoformat()}"
    )
    if notes:
        notice_body += f"\nNotes: {notes}"

    comm = Communication(
        matter_id=matter_id,
        sender_id=sender_stakeholder.id,
        type=CommunicationType.distribution_notice,
        subject=f"Distribution Notice: {description}",
        body=notice_body,
        visibility=CommunicationVisibility.all_stakeholders,
        acknowledged_by=[],
    )
    db.add(comm)
    await db.flush()

    # Update asset status if fully distributed
    if asset is not None and asset.status != AssetStatus.distributed:
        asset.status = AssetStatus.distributed
        await db.flush()

    # Log event
    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="distribution",
        entity_id=dist.id,
        action="recorded",
        metadata={
            "beneficiary_id": str(beneficiary_stakeholder_id),
            "beneficiary_name": beneficiary.full_name,
            "amount": str(amount) if amount else None,
            "distribution_type": distribution_type.value,
            "asset_id": str(asset_id) if asset_id else None,
        },
    )

    # Email notification stub
    logger.info(
        "distribution_email_notification",
        extra={
            "distribution_id": str(dist.id),
            "beneficiary_email": beneficiary.email,
            "amount": str(amount),
        },
    )

    # Reload with relationships
    return await _get_distribution_or_404(db, dist_id=dist.id, matter_id=matter_id)


# ---------------------------------------------------------------------------
# List distributions
# ---------------------------------------------------------------------------


async def list_distributions(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    page: int = 1,
    per_page: int = 50,
    beneficiary_id: uuid.UUID | None = None,
) -> tuple[list[Distribution], int]:
    """List distributions for a matter with optional beneficiary filter."""
    filters: list[Any] = [Distribution.matter_id == matter_id]
    if beneficiary_id is not None:
        filters.append(Distribution.beneficiary_stakeholder_id == beneficiary_id)

    # Count
    count_q = select(func.count()).select_from(Distribution).where(*filters)
    total = (await db.execute(count_q)).scalar_one()

    # Data
    q = (
        select(Distribution)
        .options(
            selectinload(Distribution.beneficiary),
            selectinload(Distribution.asset),
        )
        .where(*filters)
        .order_by(Distribution.distribution_date.desc(), Distribution.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    distributions = list(result.scalars().unique().all())

    return distributions, total


# ---------------------------------------------------------------------------
# Acknowledge receipt
# ---------------------------------------------------------------------------


async def acknowledge_receipt(
    db: AsyncSession,
    *,
    dist_id: uuid.UUID,
    matter_id: uuid.UUID,
    stakeholder: Stakeholder,
    current_user: CurrentUser,
) -> Distribution:
    """Beneficiary acknowledges receipt of a distribution."""
    dist = await _get_distribution_or_404(db, dist_id=dist_id, matter_id=matter_id)

    # Only the beneficiary of this distribution can acknowledge
    if dist.beneficiary_stakeholder_id != stakeholder.id:
        raise PermissionDeniedError(
            detail="Only the beneficiary of this distribution can acknowledge receipt"
        )

    if not dist.receipt_acknowledged:
        dist.receipt_acknowledged = True
        dist.receipt_acknowledged_at = datetime.now(UTC)
        await db.flush()

        await event_logger.log(
            db,
            matter_id=matter_id,
            actor_id=current_user.user_id,
            actor_type=ActorType.user,
            entity_type="distribution",
            entity_id=dist.id,
            action="receipt_acknowledged",
            metadata={
                "beneficiary_id": str(stakeholder.id),
                "beneficiary_name": stakeholder.full_name,
            },
        )

    return dist


# ---------------------------------------------------------------------------
# Distribution summary
# ---------------------------------------------------------------------------


async def get_distribution_summary(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
) -> dict[str, Any]:
    """Get distribution summary by beneficiary and type."""

    # Per-beneficiary summary
    bene_q = (
        select(
            Distribution.beneficiary_stakeholder_id,
            Stakeholder.full_name,
            func.coalesce(func.sum(Distribution.amount), Decimal(0)).label("total"),
            func.count(Distribution.id).label("count"),
            func.sum(case((Distribution.receipt_acknowledged.is_(True), 1), else_=0)).label(
                "acked"
            ),
            func.sum(case((Distribution.receipt_acknowledged.is_(False), 1), else_=0)).label(
                "pending"
            ),
        )
        .join(Stakeholder, Distribution.beneficiary_stakeholder_id == Stakeholder.id)
        .where(Distribution.matter_id == matter_id)
        .group_by(Distribution.beneficiary_stakeholder_id, Stakeholder.full_name)
    )
    bene_result = await db.execute(bene_q)
    bene_rows = bene_result.all()

    by_beneficiary = [
        {
            "stakeholder_id": row.beneficiary_stakeholder_id,
            "beneficiary_name": row.full_name,
            "total_distributed": row.total or Decimal(0),
            "distribution_count": row.count,
            "acknowledged_count": row.acked,
            "pending_count": row.pending,
        }
        for row in bene_rows
    ]

    # By type summary
    type_q = (
        select(
            Distribution.distribution_type,
            func.coalesce(func.sum(Distribution.amount), Decimal(0)).label("total"),
        )
        .where(Distribution.matter_id == matter_id)
        .group_by(Distribution.distribution_type)
    )
    type_result = await db.execute(type_q)
    by_type = {row.distribution_type.value: row.total or Decimal(0) for row in type_result.all()}

    # Totals
    totals_q = select(
        func.coalesce(func.sum(Distribution.amount), Decimal(0)).label("total_amount"),
        func.count(Distribution.id).label("total_count"),
        func.sum(case((Distribution.receipt_acknowledged.is_(True), 1), else_=0)).label("acked"),
        func.sum(case((Distribution.receipt_acknowledged.is_(False), 1), else_=0)).label("pending"),
    ).where(Distribution.matter_id == matter_id)
    totals = (await db.execute(totals_q)).one()

    return {
        "total_distributed": totals.total_amount or Decimal(0),
        "total_distributions": totals.total_count,
        "total_acknowledged": totals.acked,
        "total_pending": totals.pending,
        "by_beneficiary": by_beneficiary,
        "by_type": by_type,
    }
