"""Entity management API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.security import get_current_user, require_firm_member, require_stakeholder
from app.models.assets import Asset
from app.models.entities import Entity
from app.models.enums import FundingStatus, StakeholderRole
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.schemas.auth import CurrentUser
from app.schemas.entities import (
    AssetBrief,
    EntityCreate,
    EntityMapResponse,
    EntityResponse,
    EntityUpdate,
    FundingDetail,
)
from app.services import entity_service

router = APIRouter()

_WRITE_ROLES = {StakeholderRole.matter_admin, StakeholderRole.professional}


def _entity_to_response(entity: Entity) -> EntityResponse:
    """Convert an Entity ORM model to EntityResponse."""
    return EntityResponse(
        id=entity.id,
        matter_id=entity.matter_id,
        entity_type=entity.entity_type,
        name=entity.name,
        trustee=entity.trustee,
        successor_trustee=entity.successor_trustee,
        trigger_conditions=entity.trigger_conditions,
        funding_status=entity.funding_status,
        distribution_rules=entity.distribution_rules,
        metadata=entity.metadata_,
        assets=[
            AssetBrief(
                id=a.id,
                title=a.title,
                asset_type=a.asset_type.value,
                current_estimated_value=a.current_estimated_value,
            )
            for a in entity.assets
        ],
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _asset_to_brief(asset: Asset) -> AssetBrief:
    """Convert an Asset ORM model to AssetBrief."""
    return AssetBrief(
        id=asset.id,
        title=asset.title,
        asset_type=asset.asset_type.value,
        current_estimated_value=asset.current_estimated_value,
    )


# ---------------------------------------------------------------------------
# POST /firms/{firm_id}/matters/{matter_id}/entities — Create entity
# ---------------------------------------------------------------------------


@router.post("", response_model=EntityResponse, status_code=201)
async def create_entity(
    firm_id: UUID,
    matter_id: UUID,
    body: EntityCreate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EntityResponse:
    """Create a new entity with optional asset linking."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(
            detail="Only matter admins and professionals can create entities"
        )

    entity = await entity_service.create_entity(
        db,
        matter_id=matter_id,
        entity_type=body.entity_type,
        name=body.name,
        trustee=body.trustee,
        successor_trustee=body.successor_trustee,
        trigger_conditions=body.trigger_conditions,
        funding_status=body.funding_status or FundingStatus.unknown,
        distribution_rules=body.distribution_rules,
        asset_ids=body.asset_ids,
        current_user=current_user,
    )
    return _entity_to_response(entity)


# ---------------------------------------------------------------------------
# GET /firms/{firm_id}/matters/{matter_id}/entities — List entities
# ---------------------------------------------------------------------------


@router.get("", response_model=list[EntityResponse])
async def list_entities(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> list[EntityResponse]:
    """List all entities for a matter with linked assets."""
    entities = await entity_service.list_entities(db, matter_id=matter_id)
    return [_entity_to_response(e) for e in entities]


# ---------------------------------------------------------------------------
# GET /firms/{firm_id}/matters/{matter_id}/entities/{entity_id} — Get detail
# ---------------------------------------------------------------------------


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity_detail(
    firm_id: UUID,
    matter_id: UUID,
    entity_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> EntityResponse:
    """Get full entity detail with all linked assets."""
    entity = await entity_service.get_entity_detail(db, entity_id=entity_id, matter_id=matter_id)
    return _entity_to_response(entity)


# ---------------------------------------------------------------------------
# PATCH /firms/{firm_id}/matters/{matter_id}/entities/{entity_id} — Update
# ---------------------------------------------------------------------------


@router.patch("/{entity_id}", response_model=EntityResponse)
async def update_entity(
    firm_id: UUID,
    matter_id: UUID,
    entity_id: UUID,
    body: EntityUpdate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EntityResponse:
    """Update an entity. If asset_ids provided, replaces all links."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(
            detail="Only matter admins and professionals can update entities"
        )

    updates = body.model_dump(exclude_unset=True)
    entity = await entity_service.update_entity(
        db,
        entity_id=entity_id,
        matter_id=matter_id,
        updates=updates,
        current_user=current_user,
    )
    return _entity_to_response(entity)


# ---------------------------------------------------------------------------
# DELETE /firms/{firm_id}/matters/{matter_id}/entities/{entity_id} — Delete
# ---------------------------------------------------------------------------


@router.delete("/{entity_id}", status_code=204)
async def delete_entity(
    firm_id: UUID,
    matter_id: UUID,
    entity_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an entity and its junction links. Does NOT delete assets."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(
            detail="Only matter admins and professionals can delete entities"
        )

    await entity_service.delete_entity(
        db,
        entity_id=entity_id,
        matter_id=matter_id,
        current_user=current_user,
    )


# ---------------------------------------------------------------------------
# GET /firms/{firm_id}/matters/{matter_id}/entity-map — Entity ownership map
# ---------------------------------------------------------------------------
# Note: This endpoint is registered on a separate router since the path
# "entity-map" doesn't follow the /entities/{id} pattern.

entity_map_router = APIRouter()


@entity_map_router.get("", response_model=EntityMapResponse)
async def get_entity_map(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> EntityMapResponse:
    """Get the entity ownership map.

    Returns all entities with assets, unassigned assets, and pour-over candidates.
    """
    result = await entity_service.get_entity_map(db, matter_id=matter_id)

    # Build funding summary
    funding_summary: list[FundingDetail] = []
    for entity in result["entities"]:
        total_value = sum(
            float(a.current_estimated_value) for a in entity.assets if a.current_estimated_value
        )
        funding_summary.append(
            FundingDetail(
                entity_id=entity.id,
                entity_name=entity.name,
                funding_status=entity.funding_status,
                funded_count=len(entity.assets),
                total_value=total_value if total_value > 0 else None,
            )
        )

    return EntityMapResponse(
        entities=[_entity_to_response(e) for e in result["entities"]],
        unassigned_assets=[_asset_to_brief(a) for a in result["unassigned_assets"]],
        pour_over_candidates=[_asset_to_brief(a) for a in result["pour_over_candidates"]],
        funding_summary=funding_summary,
    )
