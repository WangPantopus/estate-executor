"""Asset management API routes."""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.security import get_current_user, require_firm_member, require_stakeholder
from app.models.enums import AssetStatus, AssetType, OwnershipType, StakeholderRole, TransferMechanism
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.schemas.auth import CurrentUser
from app.schemas.assets import (
    AssetCreate,
    AssetDetailResponse,
    AssetLinkDocument,
    AssetListItem,
    AssetListResponse,
    AssetUpdate,
    AssetValuation,
    DocumentBrief,
    EntityBrief,
    ValuationEntry,
)
from app.schemas.common import PaginationMeta, PaginationParams
from app.services import asset_service

router = APIRouter()

_WRITE_ROLES = {StakeholderRole.matter_admin, StakeholderRole.professional}


# ---------------------------------------------------------------------------
# POST /firms/{firm_id}/matters/{matter_id}/assets — Create asset
# ---------------------------------------------------------------------------


@router.post("", response_model=AssetListItem, status_code=201)
async def create_asset(
    firm_id: UUID,
    matter_id: UUID,
    body: AssetCreate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetListItem:
    """Create a new asset. Requires matter_admin or professional role."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Only matter admins and professionals can create assets")

    asset = await asset_service.create_asset(
        db,
        matter_id=matter_id,
        asset_type=body.asset_type,
        title=body.title,
        description=body.description,
        institution=body.institution,
        account_number=body.account_number,
        ownership_type=body.ownership_type,
        transfer_mechanism=body.transfer_mechanism,
        date_of_death_value=body.date_of_death_value,
        current_estimated_value=body.current_estimated_value,
        metadata=body.metadata,
        current_user=current_user,
    )
    return AssetListItem(
        id=asset.id,
        matter_id=asset.matter_id,
        asset_type=asset.asset_type,
        title=asset.title,
        description=asset.description,
        institution=asset.institution,
        account_number_masked=asset_service.mask_account_number(asset.account_number_encrypted),
        ownership_type=asset.ownership_type,
        transfer_mechanism=asset.transfer_mechanism,
        status=asset.status,
        date_of_death_value=asset.date_of_death_value,
        current_estimated_value=asset.current_estimated_value,
        final_appraised_value=asset.final_appraised_value,
        metadata=asset.metadata_,
        document_count=0,
        entities=[],
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /firms/{firm_id}/matters/{matter_id}/assets — List assets
# ---------------------------------------------------------------------------


@router.get("", response_model=AssetListResponse)
async def list_assets(
    firm_id: UUID,
    matter_id: UUID,
    asset_type: AssetType | None = Query(None),
    ownership_type: OwnershipType | None = Query(None),
    transfer_mechanism: TransferMechanism | None = Query(None),
    status: AssetStatus | None = Query(None),
    search: str | None = Query(None, description="Search title or institution"),
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> AssetListResponse:
    """List assets with filters, entity briefs, document count, and pagination."""
    items, total = await asset_service.list_assets(
        db,
        matter_id=matter_id,
        asset_type=asset_type,
        ownership_type=ownership_type,
        transfer_mechanism=transfer_mechanism,
        status=status,
        search=search,
        page=pagination.page,
        per_page=pagination.per_page,
    )
    return AssetListResponse(
        data=[AssetListItem(**item) for item in items],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0,
        ),
    )


# ---------------------------------------------------------------------------
# GET /firms/{firm_id}/matters/{matter_id}/assets/{asset_id} — Asset detail
# ---------------------------------------------------------------------------


@router.get("/{asset_id}", response_model=AssetDetailResponse)
async def get_asset_detail(
    firm_id: UUID,
    matter_id: UUID,
    asset_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> AssetDetailResponse:
    """Get full asset detail with documents, entities, and valuations history."""
    detail = await asset_service.get_asset_detail(db, asset_id=asset_id, matter_id=matter_id)
    return AssetDetailResponse(
        id=detail["id"],
        matter_id=detail["matter_id"],
        asset_type=detail["asset_type"],
        title=detail["title"],
        description=detail["description"],
        institution=detail["institution"],
        account_number_masked=detail["account_number_masked"],
        ownership_type=detail["ownership_type"],
        transfer_mechanism=detail["transfer_mechanism"],
        status=detail["status"],
        date_of_death_value=detail["date_of_death_value"],
        current_estimated_value=detail["current_estimated_value"],
        final_appraised_value=detail["final_appraised_value"],
        metadata=detail["metadata"],
        documents=[DocumentBrief(**d) for d in detail["documents"]],
        entities=[EntityBrief(**e) for e in detail["entities"]],
        valuations=[ValuationEntry(**v) for v in detail["valuations"]],
        created_at=detail["created_at"],
        updated_at=detail["updated_at"],
    )


# ---------------------------------------------------------------------------
# PATCH /firms/{firm_id}/matters/{matter_id}/assets/{asset_id} — Update asset
# ---------------------------------------------------------------------------


@router.patch("/{asset_id}", response_model=AssetListItem)
async def update_asset(
    firm_id: UUID,
    matter_id: UUID,
    asset_id: UUID,
    body: AssetUpdate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetListItem:
    """Update an asset with status lifecycle enforcement."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Only matter admins and professionals can update assets")

    updates = body.model_dump(exclude_unset=True)
    asset = await asset_service.update_asset(
        db,
        asset_id=asset_id,
        matter_id=matter_id,
        updates=updates,
        current_user=current_user,
    )
    return _asset_to_list_item(asset)


# ---------------------------------------------------------------------------
# DELETE /firms/{firm_id}/matters/{matter_id}/assets/{asset_id} — Delete asset
# ---------------------------------------------------------------------------


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(
    firm_id: UUID,
    matter_id: UUID,
    asset_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an asset. Only allowed if status is 'discovered'."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Only matter admins and professionals can delete assets")

    await asset_service.delete_asset(
        db,
        asset_id=asset_id,
        matter_id=matter_id,
        current_user=current_user,
    )


# ---------------------------------------------------------------------------
# POST .../assets/{asset_id}/documents — Link document to asset
# ---------------------------------------------------------------------------


@router.post("/{asset_id}/documents", status_code=201)
async def link_document(
    firm_id: UUID,
    matter_id: UUID,
    asset_id: UUID,
    body: AssetLinkDocument,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Link a document to an asset."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Only matter admins and professionals can link documents")

    await asset_service.link_document(
        db,
        asset_id=asset_id,
        matter_id=matter_id,
        document_id=body.document_id,
        current_user=current_user,
    )
    return {"status": "linked"}


# ---------------------------------------------------------------------------
# POST .../assets/{asset_id}/valuations — Add valuation
# ---------------------------------------------------------------------------


@router.post("/{asset_id}/valuations", response_model=AssetListItem)
async def add_valuation(
    firm_id: UUID,
    matter_id: UUID,
    asset_id: UUID,
    body: AssetValuation,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetListItem:
    """Add a valuation to an asset."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Only matter admins and professionals can add valuations")

    asset = await asset_service.add_valuation(
        db,
        asset_id=asset_id,
        matter_id=matter_id,
        valuation_type=body.type,
        value=body.value,
        notes=body.notes,
        current_user=current_user,
    )
    return _asset_to_list_item(asset)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _asset_to_list_item(asset: Asset) -> AssetListItem:
    """Convert an Asset ORM model to AssetListItem."""
    import contextlib

    entities: list[EntityBrief] = []
    doc_count = 0
    with contextlib.suppress(Exception):
        entities = [
            EntityBrief(id=e.id, name=e.name, entity_type=e.entity_type.value)
            for e in asset.entities
        ]
    with contextlib.suppress(Exception):
        doc_count = len(asset.documents)

    return AssetListItem(
        id=asset.id,
        matter_id=asset.matter_id,
        asset_type=asset.asset_type,
        title=asset.title,
        description=asset.description,
        institution=asset.institution,
        account_number_masked=asset_service.mask_account_number(asset.account_number_encrypted),
        ownership_type=asset.ownership_type,
        transfer_mechanism=asset.transfer_mechanism,
        status=asset.status,
        date_of_death_value=asset.date_of_death_value,
        current_estimated_value=asset.current_estimated_value,
        final_appraised_value=asset.final_appraised_value,
        metadata=asset.metadata_,
        document_count=doc_count,
        entities=entities,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )
