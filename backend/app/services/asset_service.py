"""Asset business logic service layer — CRUD, lifecycle, valuations, and encryption."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.events import event_logger
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import decrypt_field, encrypt_field
from app.models.asset_documents import asset_documents
from app.models.assets import Asset
from app.models.documents import Document
from app.models.enums import ActorType, AssetStatus, AssetType, OwnershipType, TransferMechanism

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Asset status lifecycle — ordered, forward-only
# ---------------------------------------------------------------------------

_STATUS_ORDER = [
    AssetStatus.discovered,
    AssetStatus.valued,
    AssetStatus.transferred,
    AssetStatus.distributed,
]
_STATUS_INDEX = {s: i for i, s in enumerate(_STATUS_ORDER)}


def _validate_status_transition(current: AssetStatus, target: AssetStatus) -> None:
    """Validate that the status transition moves forward in the lifecycle."""
    cur_idx = _STATUS_INDEX.get(current)
    tgt_idx = _STATUS_INDEX.get(target)
    if cur_idx is None or tgt_idx is None:
        raise BadRequestError(detail=f"Unknown asset status: {current} or {target}")
    if tgt_idx <= cur_idx:
        raise ConflictError(
            detail=f"Cannot transition from '{current.value}' to '{target.value}'. "
            f"Asset status can only move forward: discovered → valued → transferred → distributed"
        )


# ---------------------------------------------------------------------------
# Account number helpers
# ---------------------------------------------------------------------------


def mask_account_number(encrypted: bytes | None) -> str | None:
    """Decrypt and mask an account number, returning only last 4 chars."""
    if encrypted is None:
        return None
    try:
        plaintext = decrypt_field(encrypted)
        if len(plaintext) <= 4:
            return "****"
        return "****" + plaintext[-4:]
    except Exception:
        logger.warning("Failed to decrypt account number — returning masked placeholder")
        return "****"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_asset_or_404(
    db: AsyncSession, *, asset_id: uuid.UUID, matter_id: uuid.UUID
) -> Asset:
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.matter_id == matter_id)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise NotFoundError(detail="Asset not found")
    return asset


# ---------------------------------------------------------------------------
# Create asset
# ---------------------------------------------------------------------------


async def create_asset(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    asset_type: AssetType,
    title: str,
    description: str | None = None,
    institution: str | None = None,
    account_number: str | None = None,
    ownership_type: OwnershipType = OwnershipType.individual,
    transfer_mechanism: TransferMechanism = TransferMechanism.probate,
    date_of_death_value: Decimal | None = None,
    current_estimated_value: Decimal | None = None,
    metadata: dict | None = None,
    current_user: CurrentUser,
) -> Asset:
    """Create a new asset with optional account number encryption."""
    encrypted_acct = encrypt_field(account_number) if account_number else None

    asset = Asset(
        matter_id=matter_id,
        asset_type=asset_type,
        title=title,
        description=description,
        institution=institution,
        account_number_encrypted=encrypted_acct,
        ownership_type=ownership_type,
        transfer_mechanism=transfer_mechanism,
        date_of_death_value=date_of_death_value,
        current_estimated_value=current_estimated_value,
        metadata_=metadata or {},
    )
    db.add(asset)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="asset",
        entity_id=asset.id,
        action="created",
        metadata={
            "asset_type": asset_type.value,
            "title": title,
        },
    )

    return asset


# ---------------------------------------------------------------------------
# List assets
# ---------------------------------------------------------------------------


async def list_assets(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    asset_type: AssetType | None = None,
    ownership_type: OwnershipType | None = None,
    transfer_mechanism: TransferMechanism | None = None,
    status: AssetStatus | None = None,
    search: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """List assets with filters, entity briefs, document count, and pagination."""
    base_filters = [Asset.matter_id == matter_id]

    if asset_type is not None:
        base_filters.append(Asset.asset_type == asset_type)
    if ownership_type is not None:
        base_filters.append(Asset.ownership_type == ownership_type)
    if transfer_mechanism is not None:
        base_filters.append(Asset.transfer_mechanism == transfer_mechanism)
    if status is not None:
        base_filters.append(Asset.status == status)
    if search:
        pattern = f"%{search}%"
        base_filters.append(
            or_(
                Asset.title.ilike(pattern),
                Asset.institution.ilike(pattern),
            )
        )

    # Count
    count_q = select(func.count()).select_from(Asset).where(*base_filters)
    total = (await db.execute(count_q)).scalar_one()

    # Query with entities eager-loaded
    q = (
        select(Asset)
        .options(selectinload(Asset.entities), selectinload(Asset.documents))
        .where(*base_filters)
        .order_by(Asset.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    assets = result.scalars().unique().all()

    items = []
    for asset in assets:
        items.append(
            {
                "id": asset.id,
                "matter_id": asset.matter_id,
                "asset_type": asset.asset_type,
                "title": asset.title,
                "description": asset.description,
                "institution": asset.institution,
                "account_number_masked": mask_account_number(asset.account_number_encrypted),
                "ownership_type": asset.ownership_type,
                "transfer_mechanism": asset.transfer_mechanism,
                "status": asset.status,
                "date_of_death_value": asset.date_of_death_value,
                "current_estimated_value": asset.current_estimated_value,
                "final_appraised_value": asset.final_appraised_value,
                "metadata": asset.metadata_,
                "document_count": len(asset.documents),
                "entities": [
                    {"id": e.id, "name": e.name, "entity_type": e.entity_type.value}
                    for e in asset.entities
                ],
                "created_at": asset.created_at,
                "updated_at": asset.updated_at,
            }
        )

    return items, total


# ---------------------------------------------------------------------------
# Get asset detail
# ---------------------------------------------------------------------------


async def get_asset_detail(
    db: AsyncSession,
    *,
    asset_id: uuid.UUID,
    matter_id: uuid.UUID,
) -> dict[str, Any]:
    """Get full asset detail including documents, entities, and valuations history."""
    result = await db.execute(
        select(Asset)
        .options(
            selectinload(Asset.documents),
            selectinload(Asset.entities),
        )
        .where(Asset.id == asset_id, Asset.matter_id == matter_id)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise NotFoundError(detail="Asset not found")

    # Build valuations history from event log
    from app.models.events import Event

    val_q = (
        select(Event)
        .where(
            Event.entity_type == "asset",
            Event.entity_id == asset_id,
            Event.action == "valuation_added",
        )
        .order_by(Event.created_at.asc())
    )
    val_result = await db.execute(val_q)
    val_events = val_result.scalars().all()

    valuations = []
    for ev in val_events:
        meta = ev.metadata_ or {}
        valuations.append(
            {
                "type": meta.get("valuation_type", ""),
                "value": Decimal(str(meta["value"]))
                if meta.get("value") is not None
                else Decimal("0"),
                "notes": meta.get("notes"),
                "recorded_at": ev.created_at,
                "recorded_by": ev.actor_id,
            }
        )

    return {
        "id": asset.id,
        "matter_id": asset.matter_id,
        "asset_type": asset.asset_type,
        "title": asset.title,
        "description": asset.description,
        "institution": asset.institution,
        "account_number_masked": mask_account_number(asset.account_number_encrypted),
        "ownership_type": asset.ownership_type,
        "transfer_mechanism": asset.transfer_mechanism,
        "status": asset.status,
        "date_of_death_value": asset.date_of_death_value,
        "current_estimated_value": asset.current_estimated_value,
        "final_appraised_value": asset.final_appraised_value,
        "metadata": asset.metadata_,
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "doc_type": doc.doc_type,
                "created_at": doc.created_at,
            }
            for doc in asset.documents
        ],
        "entities": [
            {"id": e.id, "name": e.name, "entity_type": e.entity_type.value} for e in asset.entities
        ],
        "valuations": valuations,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }


# ---------------------------------------------------------------------------
# Update asset
# ---------------------------------------------------------------------------


async def update_asset(
    db: AsyncSession,
    *,
    asset_id: uuid.UUID,
    matter_id: uuid.UUID,
    updates: dict[str, Any],
    current_user: CurrentUser,
) -> Asset:
    """Update an asset with status lifecycle enforcement and changes diff."""
    asset = await _get_asset_or_404(db, asset_id=asset_id, matter_id=matter_id)

    changes: dict[str, dict[str, Any]] = {}

    # Handle status transition
    new_status = updates.pop("status", None)
    if new_status is not None:
        _validate_status_transition(asset.status, new_status)
        changes["status"] = {"old": asset.status.value, "new": new_status.value}
        asset.status = new_status

    # Handle account_number encryption
    account_number = updates.pop("account_number", None)
    if account_number is not None:
        asset.account_number_encrypted = encrypt_field(account_number)
        changes["account_number"] = {"old": "****", "new": "****"}

    # Handle metadata
    metadata = updates.pop("metadata", None)
    if metadata is not None:
        asset.metadata_ = metadata
        changes["metadata"] = {"old": "...", "new": "..."}

    # Apply remaining scalar fields
    for field, value in updates.items():
        if hasattr(asset, field):
            old_val = getattr(asset, field)
            old_str = old_val.value if hasattr(old_val, "value") else old_val
            new_str = value.value if hasattr(value, "value") else value
            if old_str != new_str:
                changes[field] = {
                    "old": str(old_str) if old_str is not None else None,
                    "new": str(new_str),
                }
                setattr(asset, field, value)

    if changes:
        await db.flush()
        await event_logger.log(
            db,
            matter_id=matter_id,
            actor_id=current_user.user_id,
            actor_type=ActorType.user,
            entity_type="asset",
            entity_id=asset.id,
            action="updated",
            changes=changes,
        )

    return asset


# ---------------------------------------------------------------------------
# Delete asset
# ---------------------------------------------------------------------------


async def delete_asset(
    db: AsyncSession,
    *,
    asset_id: uuid.UUID,
    matter_id: uuid.UUID,
    current_user: CurrentUser,
) -> None:
    """Delete an asset. Only allowed if status is 'discovered'."""
    asset = await _get_asset_or_404(db, asset_id=asset_id, matter_id=matter_id)

    if asset.status != AssetStatus.discovered:
        raise ConflictError(
            detail=f"Cannot delete asset in '{asset.status.value}' status. "
            f"Only assets in 'discovered' status can be deleted."
        )

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="asset",
        entity_id=asset.id,
        action="deleted",
        metadata={"title": asset.title, "asset_type": asset.asset_type.value},
    )

    await db.delete(asset)
    await db.flush()


# ---------------------------------------------------------------------------
# Link document
# ---------------------------------------------------------------------------


async def link_document(
    db: AsyncSession,
    *,
    asset_id: uuid.UUID,
    matter_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: CurrentUser,
) -> None:
    """Link a document to an asset via the asset_documents junction table."""
    await _get_asset_or_404(db, asset_id=asset_id, matter_id=matter_id)

    # Validate document belongs to same matter
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.matter_id == matter_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise BadRequestError(detail="Document not found on this matter")

    # Check for existing link
    existing_q = select(asset_documents).where(
        asset_documents.c.asset_id == asset_id,
        asset_documents.c.document_id == document_id,
    )
    if (await db.execute(existing_q)).first() is not None:
        raise ConflictError(detail="Document is already linked to this asset")

    await db.execute(asset_documents.insert().values(asset_id=asset_id, document_id=document_id))
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="asset",
        entity_id=asset_id,
        action="document_linked",
        metadata={"document_id": str(document_id)},
    )


# ---------------------------------------------------------------------------
# Add valuation
# ---------------------------------------------------------------------------

_VALUATION_FIELD_MAP = {
    "date_of_death": "date_of_death_value",
    "current_estimate": "current_estimated_value",
    "final_appraised": "final_appraised_value",
}


async def add_valuation(
    db: AsyncSession,
    *,
    asset_id: uuid.UUID,
    matter_id: uuid.UUID,
    valuation_type: str,
    value: Decimal,
    notes: str | None = None,
    current_user: CurrentUser,
) -> Asset:
    """Add a valuation to an asset.

    Updates the appropriate value field. If setting final_appraised_value
    and status is 'discovered', auto-transitions to 'valued'.
    """
    asset = await _get_asset_or_404(db, asset_id=asset_id, matter_id=matter_id)

    field_name = _VALUATION_FIELD_MAP.get(valuation_type)
    if field_name is None:
        raise BadRequestError(
            detail=f"Invalid valuation type '{valuation_type}'. "
            f"Must be one of: date_of_death, current_estimate, final_appraised"
        )

    old_value = getattr(asset, field_name)
    setattr(asset, field_name, value)

    # Auto-transition: final_appraised + discovered → valued
    status_changed = False
    if valuation_type == "final_appraised" and asset.status == AssetStatus.discovered:
        asset.status = AssetStatus.valued
        status_changed = True

    await db.flush()

    event_meta: dict[str, Any] = {
        "valuation_type": valuation_type,
        "value": str(value),
        "old_value": str(old_value) if old_value is not None else None,
    }
    if notes:
        event_meta["notes"] = notes
    if status_changed:
        event_meta["status_changed"] = {"old": "discovered", "new": "valued"}

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="asset",
        entity_id=asset.id,
        action="valuation_added",
        metadata=event_meta,
    )

    return asset
