"""Entity business logic service layer — CRUD, asset linking, and ownership map."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.core.events import event_logger
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.assets import Asset
from app.models.entities import Entity
from app.models.entity_assets import entity_assets
from app.models.enums import ActorType, EntityType, FundingStatus, TransferMechanism

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_entity_or_404(
    db: AsyncSession, *, entity_id: uuid.UUID, matter_id: uuid.UUID
) -> Entity:
    result = await db.execute(
        select(Entity)
        .options(selectinload(Entity.assets))
        .where(Entity.id == entity_id, Entity.matter_id == matter_id)
    )
    entity = result.scalar_one_or_none()
    if entity is None:
        raise NotFoundError(detail="Entity not found")
    return entity


async def _validate_asset_ids(
    db: AsyncSession, *, asset_ids: list[uuid.UUID], matter_id: uuid.UUID
) -> None:
    """Validate that all asset IDs belong to the given matter."""
    if not asset_ids:
        return
    result = await db.execute(
        select(func.count())
        .select_from(Asset)
        .where(Asset.id.in_(asset_ids), Asset.matter_id == matter_id)
    )
    found = result.scalar_one()
    if found != len(set(asset_ids)):
        raise BadRequestError(
            detail="One or more asset IDs not found on this matter"
        )


async def _set_asset_links(
    db: AsyncSession, *, entity_id: uuid.UUID, asset_ids: list[uuid.UUID]
) -> None:
    """Replace all entity_asset links for an entity (set semantics)."""
    # Delete existing links
    await db.execute(
        delete(entity_assets).where(entity_assets.c.entity_id == entity_id)
    )
    # Insert new links
    if asset_ids:
        unique_ids = list(set(asset_ids))
        await db.execute(
            entity_assets.insert(),
            [{"entity_id": entity_id, "asset_id": aid} for aid in unique_ids],
        )


# ---------------------------------------------------------------------------
# Create entity
# ---------------------------------------------------------------------------


async def create_entity(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    entity_type: EntityType,
    name: str,
    trustee: str | None = None,
    successor_trustee: str | None = None,
    trigger_conditions: dict | None = None,
    funding_status: FundingStatus = FundingStatus.unknown,
    distribution_rules: dict | None = None,
    asset_ids: list[uuid.UUID] | None = None,
    current_user: CurrentUser,
) -> Entity:
    """Create a new entity with optional asset linking."""
    entity = Entity(
        matter_id=matter_id,
        entity_type=entity_type,
        name=name,
        trustee=trustee,
        successor_trustee=successor_trustee,
        trigger_conditions=trigger_conditions,
        funding_status=funding_status or FundingStatus.unknown,
        distribution_rules=distribution_rules,
        metadata_={},
    )
    db.add(entity)
    await db.flush()

    # Link assets if provided
    if asset_ids:
        await _validate_asset_ids(db, asset_ids=asset_ids, matter_id=matter_id)
        await _set_asset_links(db, entity_id=entity.id, asset_ids=asset_ids)

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="entity",
        entity_id=entity.id,
        action="created",
        metadata={
            "entity_type": entity_type.value,
            "name": name,
            "asset_count": len(asset_ids) if asset_ids else 0,
        },
    )

    # Reload with assets relationship
    return await _get_entity_or_404(db, entity_id=entity.id, matter_id=matter_id)


# ---------------------------------------------------------------------------
# List entities
# ---------------------------------------------------------------------------


async def list_entities(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
) -> list[Entity]:
    """List all entities for a matter with linked assets."""
    result = await db.execute(
        select(Entity)
        .options(selectinload(Entity.assets))
        .where(Entity.matter_id == matter_id)
        .order_by(Entity.created_at.desc())
    )
    return list(result.scalars().unique().all())


# ---------------------------------------------------------------------------
# Get entity detail
# ---------------------------------------------------------------------------


async def get_entity_detail(
    db: AsyncSession,
    *,
    entity_id: uuid.UUID,
    matter_id: uuid.UUID,
) -> Entity:
    """Get full entity detail with all linked assets."""
    return await _get_entity_or_404(db, entity_id=entity_id, matter_id=matter_id)


# ---------------------------------------------------------------------------
# Update entity
# ---------------------------------------------------------------------------


async def update_entity(
    db: AsyncSession,
    *,
    entity_id: uuid.UUID,
    matter_id: uuid.UUID,
    updates: dict[str, Any],
    current_user: CurrentUser,
) -> Entity:
    """Update an entity. If asset_ids provided, replaces all links (set semantics)."""
    entity = await _get_entity_or_404(db, entity_id=entity_id, matter_id=matter_id)

    changes: dict[str, dict[str, Any]] = {}

    # Handle asset_ids replacement
    asset_ids = updates.pop("asset_ids", None)
    if asset_ids is not None:
        await _validate_asset_ids(db, asset_ids=asset_ids, matter_id=matter_id)
        old_ids = sorted(str(a.id) for a in entity.assets)
        new_ids = sorted(str(aid) for aid in asset_ids)
        if old_ids != new_ids:
            changes["asset_ids"] = {"old": old_ids, "new": new_ids}
        await _set_asset_links(db, entity_id=entity.id, asset_ids=asset_ids)

    # Apply scalar field updates
    for field, value in updates.items():
        if hasattr(entity, field):
            old_val = getattr(entity, field)
            old_str = old_val.value if hasattr(old_val, "value") else old_val
            new_str = value.value if hasattr(value, "value") else value
            if old_str != new_str:
                changes[field] = {
                    "old": str(old_str) if old_str is not None else None,
                    "new": str(new_str) if new_str is not None else None,
                }
                setattr(entity, field, value)

    if changes:
        await db.flush()
        await event_logger.log(
            db,
            matter_id=matter_id,
            actor_id=current_user.user_id,
            actor_type=ActorType.user,
            entity_type="entity",
            entity_id=entity.id,
            action="updated",
            changes=changes,
        )

    # Reload to get fresh asset relationships
    return await _get_entity_or_404(db, entity_id=entity.id, matter_id=matter_id)


# ---------------------------------------------------------------------------
# Delete entity
# ---------------------------------------------------------------------------


async def delete_entity(
    db: AsyncSession,
    *,
    entity_id: uuid.UUID,
    matter_id: uuid.UUID,
    current_user: CurrentUser,
) -> None:
    """Delete an entity and its junction links. Does NOT delete the assets."""
    entity = await _get_entity_or_404(db, entity_id=entity_id, matter_id=matter_id)

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="entity",
        entity_id=entity.id,
        action="deleted",
        metadata={"name": entity.name, "entity_type": entity.entity_type.value},
    )

    # CASCADE on entity_assets will remove junction rows
    await db.delete(entity)
    await db.flush()


# ---------------------------------------------------------------------------
# Entity ownership map
# ---------------------------------------------------------------------------

# Trust entity types for pour-over detection
_TRUST_ENTITY_TYPES = {
    EntityType.revocable_trust,
    EntityType.irrevocable_trust,
}


async def get_entity_map(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
) -> dict[str, Any]:
    """Get the entity ownership map.

    Returns:
        entities: All entities with their linked assets
        unassigned_assets: Assets not linked to any entity
        pour_over_candidates: Assets with transfer_mechanism='probate'
            on matters that have trust entities (potential pour-over will items)
    """
    # 1. Load all entities with assets
    entities_result = await db.execute(
        select(Entity)
        .options(selectinload(Entity.assets))
        .where(Entity.matter_id == matter_id)
        .order_by(Entity.created_at.asc())
    )
    entities = list(entities_result.scalars().unique().all())

    # 2. Get all asset IDs linked to any entity
    linked_asset_ids: set[uuid.UUID] = set()
    for ent in entities:
        for asset in ent.assets:
            linked_asset_ids.add(asset.id)

    # 3. Load all assets for this matter
    all_assets_result = await db.execute(
        select(Asset)
        .where(Asset.matter_id == matter_id)
        .order_by(Asset.created_at.asc())
    )
    all_assets = list(all_assets_result.scalars().all())

    # 4. Unassigned assets: not linked to any entity
    unassigned = [a for a in all_assets if a.id not in linked_asset_ids]

    # 5. Pour-over candidates: probate assets when trust entities exist
    has_trust = any(e.entity_type in _TRUST_ENTITY_TYPES for e in entities)
    pour_over: list[Asset] = []
    if has_trust:
        pour_over = [
            a for a in all_assets
            if a.transfer_mechanism == TransferMechanism.probate
        ]

    return {
        "entities": entities,
        "unassigned_assets": unassigned,
        "pour_over_candidates": pour_over,
    }
