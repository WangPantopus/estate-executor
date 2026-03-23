"""AI feature API routes — classification, extraction, letter drafting."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.security import get_current_user, require_firm_member, require_stakeholder
from app.models.enums import StakeholderRole
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.schemas.ai import AIExtractResponse
from app.schemas.auth import CurrentUser

router = APIRouter()

_WRITE_ROLES = {
    StakeholderRole.matter_admin,
    StakeholderRole.professional,
    StakeholderRole.executor_trustee,
}


# ---------------------------------------------------------------------------
# POST .../ai/extract/{doc_id} — Trigger AI data extraction
# ---------------------------------------------------------------------------


@router.post("/extract/{doc_id}", response_model=AIExtractResponse)
async def extract_document_data(
    firm_id: UUID,
    matter_id: UUID,
    doc_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AIExtractResponse:
    """Manually trigger AI data extraction on a classified document.

    The document must already be classified (have a doc_type).
    Extraction runs synchronously and returns extracted fields.
    """
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Insufficient permissions for AI extraction")

    from app.services.ai_extraction_service import extract_document_data as do_extract

    try:
        result = await do_extract(db, document_id=doc_id)
    except ValueError as exc:
        raise NotFoundError(detail=str(exc)) from exc

    return result
