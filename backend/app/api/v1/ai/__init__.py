"""AI feature API routes — classification, extraction, letter drafting, suggestions, anomalies.

All AI endpoints handle service unavailability gracefully:
- ValueError → 404 (missing entity)
- RateLimitExceededError → 429 (too many requests)
- API/connection errors → 503 (AI service temporarily unavailable)
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.security import get_current_user, require_firm_member, require_stakeholder
from app.models.enums import StakeholderRole
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.schemas.ai import AILetterDraftRequest
from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter()

_WRITE_ROLES = {
    StakeholderRole.matter_admin,
    StakeholderRole.professional,
    StakeholderRole.executor_trustee,
}


def _handle_ai_error(exc: Exception, operation: str) -> JSONResponse:
    """Convert AI service errors to appropriate HTTP responses."""
    from app.services.ai_rate_limiter import RateLimitExceededError

    if isinstance(exc, RateLimitExceededError):
        return JSONResponse(
            status_code=429,
            content={
                "detail": "AI rate limit exceeded. Please try again later.",
                "error_type": "rate_limit_exceeded",
            },
        )

    # Log the error for monitoring
    logger.warning(
        "ai_service_error",
        extra={"operation": operation, "error": str(exc)},
        exc_info=True,
    )

    return JSONResponse(
        status_code=503,
        content={
            "detail": "AI service is temporarily unavailable. You can still use manual features.",
            "error_type": "ai_unavailable",
        },
    )


# ---------------------------------------------------------------------------
# POST .../ai/extract/{doc_id} — Trigger AI data extraction
# ---------------------------------------------------------------------------


@router.post("/extract/{doc_id}", response_model=None)
async def extract_document_data(
    firm_id: UUID,
    matter_id: UUID,
    doc_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Manually trigger AI data extraction on a classified document."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Insufficient permissions for AI extraction")

    from app.services.ai_extraction_service import extract_document_data as do_extract

    try:
        return await do_extract(db, document_id=doc_id)
    except ValueError as exc:
        raise NotFoundError(detail=str(exc)) from exc
    except Exception as exc:
        return _handle_ai_error(exc, "extract")


# ---------------------------------------------------------------------------
# POST .../ai/draft-letter — Draft an estate administration letter
# ---------------------------------------------------------------------------


@router.post("/draft-letter", response_model=None)
async def draft_letter(
    firm_id: UUID,
    matter_id: UUID,
    body: AILetterDraftRequest,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Draft a formal notification or claim letter for an asset."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Insufficient permissions for AI letter drafting")

    from app.services.ai_letter_service import draft_letter as do_draft

    try:
        return await do_draft(
            db,
            matter_id=matter_id,
            asset_id=body.asset_id,
            letter_type=body.letter_type,
        )
    except ValueError as exc:
        raise NotFoundError(detail=str(exc)) from exc
    except Exception as exc:
        return _handle_ai_error(exc, "draft_letter")


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


@router.post("/suggest-tasks", response_model=None)
async def suggest_tasks(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get AI-powered task suggestions based on the estate's asset profile."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Insufficient permissions for AI suggestions")

    from app.services.ai_suggestion_service import suggest_tasks as do_suggest

    try:
        return await do_suggest(db, matter_id=matter_id)
    except ValueError as exc:
        raise NotFoundError(detail=str(exc)) from exc
    except Exception as exc:
        return _handle_ai_error(exc, "suggest_tasks")


# ---------------------------------------------------------------------------
# POST .../ai/detect-anomalies — AI anomaly detection
# ---------------------------------------------------------------------------


@router.post("/detect-anomalies", response_model=None)
async def detect_anomalies(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Detect anomalies by comparing AI-extracted document data against the asset registry."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Insufficient permissions for anomaly detection")

    from app.services.ai_anomaly_service import detect_anomalies as do_detect

    try:
        return await do_detect(db, matter_id=matter_id)
    except ValueError as exc:
        raise NotFoundError(detail=str(exc)) from exc
    except Exception as exc:
        return _handle_ai_error(exc, "detect_anomalies")


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
) -> Any:
    """Analyze a trust document for entity creation and funding suggestions."""
    if stakeholder.role not in _WRITE_ROLES:
        raise PermissionDeniedError(detail="Insufficient permissions for trust analysis")

    from app.services.ai_trust_analysis_service import analyze_trust_document as do_analyze

    try:
        return await do_analyze(db, document_id=doc_id, matter_id=matter_id)
    except ValueError as exc:
        raise NotFoundError(detail=str(exc)) from exc
    except Exception as exc:
        return _handle_ai_error(exc, "trust_analysis")


# ---------------------------------------------------------------------------
# GET .../ai/usage-stats — AI usage monitoring
# ---------------------------------------------------------------------------


@router.get("/usage-stats")
async def get_usage_stats(
    firm_id: UUID,
    matter_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get AI usage statistics for the firm."""
    if stakeholder.role not in {StakeholderRole.matter_admin, StakeholderRole.professional}:
        raise PermissionDeniedError(detail="Only admins can view AI usage stats")

    from app.services.ai_usage_service import get_usage_stats as do_get_stats

    return await do_get_stats(db, firm_id=firm_id)
