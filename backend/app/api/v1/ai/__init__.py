"""AI feature API routes — classification, extraction, letter drafting, suggestions, anomalies."""

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
from app.schemas.ai import (
    AIAnomalyResponse,
    AIExtractResponse,
    AILetterDraftRequest,
    AILetterDraftResponse,
    AISuggestTasksResponse,
)
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


# ---------------------------------------------------------------------------
# POST .../ai/draft-letter — Draft an estate administration letter
# ---------------------------------------------------------------------------


@router.post("/draft-letter", response_model=AILetterDraftResponse)
async def draft_letter(
    firm_id: UUID,
    matter_id: UUID,
    body: AILetterDraftRequest,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AILetterDraftResponse:
    """Draft a formal notification or claim letter for an asset.

    Uses AI to generate a professional letter based on matter context,
    asset details, and the specified letter type.
    """
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Insufficient permissions for AI letter drafting")

    from app.services.ai_letter_service import draft_letter as do_draft

    try:
        result = await do_draft(
            db,
            matter_id=matter_id,
            asset_id=body.asset_id,
            letter_type=body.letter_type,
        )
    except ValueError as exc:
        raise NotFoundError(detail=str(exc)) from exc

    return result


# ---------------------------------------------------------------------------
# GET .../ai/letter-types — List available letter types
# ---------------------------------------------------------------------------


@router.get("/letter-types")
async def list_letter_types(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
) -> list[dict[str, str]]:
    """List available letter types for drafting."""
    from app.services.ai_letter_service import LETTER_TYPES

    return [
        {"key": key, "label": val["label"], "description": val["description"]}
        for key, val in LETTER_TYPES.items()
    ]


# ---------------------------------------------------------------------------
# POST .../ai/suggest-tasks — AI task suggestions
# ---------------------------------------------------------------------------


@router.post("/suggest-tasks", response_model=AISuggestTasksResponse)
async def suggest_tasks(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AISuggestTasksResponse:
    """Get AI-powered task suggestions based on the estate's asset profile.

    Analyzes assets, entities, existing tasks, and documents to suggest
    additional tasks that may be needed.
    """
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Insufficient permissions for AI suggestions")

    from app.services.ai_suggestion_service import suggest_tasks as do_suggest

    try:
        result = await do_suggest(db, matter_id=matter_id)
    except ValueError as exc:
        raise NotFoundError(detail=str(exc)) from exc

    return result


# ---------------------------------------------------------------------------
# POST .../ai/detect-anomalies — AI anomaly detection
# ---------------------------------------------------------------------------


@router.post("/detect-anomalies", response_model=AIAnomalyResponse)
async def detect_anomalies(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AIAnomalyResponse:
    """Detect anomalies by comparing AI-extracted document data against the asset registry.

    Identifies missing assets, value discrepancies, unregistered stakeholders,
    and missing tasks.
    """
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Insufficient permissions for anomaly detection")

    from app.services.ai_anomaly_service import detect_anomalies as do_detect

    try:
        result = await do_detect(db, matter_id=matter_id)
    except ValueError as exc:
        raise NotFoundError(detail=str(exc)) from exc

    return result


# ---------------------------------------------------------------------------
# POST .../ai/analyze-trust/{doc_id} — AI trust document analysis
# ---------------------------------------------------------------------------


@router.post("/analyze-trust/{doc_id}")
async def analyze_trust_document(
    firm_id: UUID,
    matter_id: UUID,
    doc_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Analyze a trust document for entity creation and funding suggestions.

    Automatically creates an entity from extracted trust details if none exists,
    then analyzes which assets should be funded into the trust.
    """
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Insufficient permissions for trust analysis")

    from app.services.ai_trust_analysis_service import analyze_trust_document as do_analyze

    try:
        result = await do_analyze(db, document_id=doc_id, matter_id=matter_id)
    except ValueError as exc:
        raise NotFoundError(detail=str(exc)) from exc

    return result
