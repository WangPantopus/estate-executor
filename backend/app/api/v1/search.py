"""Search API — full-text search across all entities within a firm."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_db
from app.core.security import get_current_user, require_firm_member
from app.schemas.search import SearchResponse, SearchResult
from app.services import search_service

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.firm_memberships import FirmMembership
    from app.schemas.auth import CurrentUser

router = APIRouter()


@router.get("", response_model=SearchResponse)
async def search(
    firm_id: UUID,
    q: str = Query(
        ...,
        min_length=1,
        max_length=200,
        description="Search query",
    ),
    entity_types: str | None = Query(
        None,
        description="Comma-separated entity types to search",
    ),
    matter_id: UUID | None = Query(None, description="Filter to a specific matter"),
    limit: int = Query(20, ge=1, le=100, description="Max results per entity type"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    _membership: FirmMembership = Depends(require_firm_member),
) -> SearchResponse:
    """Search across matters, tasks, assets, documents, and communications.

    Returns results ranked by relevance with highlighted snippets.
    """
    types_list = None
    if entity_types:
        types_list = [t.strip() for t in entity_types.split(",") if t.strip()]

    results = await search_service.search(
        db,
        firm_id=firm_id,
        query=q,
        entity_types=types_list,
        matter_id=matter_id,
        limit=limit,
    )

    # Build response with grouping
    groups: dict[str, int] = {}
    for r in results:
        et = r["entity_type"]
        groups[et] = groups.get(et, 0) + 1

    return SearchResponse(
        query=q,
        total=len(results),
        results=[SearchResult(**r) for r in results],
        groups=groups,
    )
