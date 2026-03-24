"""Privacy API — GDPR/CCPA data export and deletion endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.security import get_current_user, require_firm_member
from app.models.enums import FirmRole, PrivacyRequestStatus, PrivacyRequestType
from app.schemas.auth import CurrentUser
from app.schemas.privacy import (
    PrivacyRequestCreate,
    PrivacyRequestListResponse,
    PrivacyRequestResponse,
    PrivacyRequestReview,
)
from app.services import privacy_service

router = APIRouter()


def _to_response(req) -> PrivacyRequestResponse:
    """Convert a PrivacyRequest model to a response schema."""
    return PrivacyRequestResponse(
        id=req.id,
        firm_id=req.firm_id,
        user_id=req.user_id,
        request_type=req.request_type.value if hasattr(req.request_type, "value") else str(req.request_type),
        status=req.status.value if hasattr(req.status, "value") else str(req.status),
        reason=req.reason,
        reviewed_by=req.reviewed_by,
        reviewed_at=req.reviewed_at,
        review_note=req.review_note,
        completed_at=req.completed_at,
        export_storage_key=req.export_storage_key,
        deletion_summary=req.deletion_summary,
        created_at=req.created_at,
        updated_at=req.updated_at,
        user_email=req.user.email if hasattr(req, "user") and req.user else None,
        user_name=req.user.full_name if hasattr(req, "user") and req.user else None,
    )


# ---------------------------------------------------------------------------
# User endpoints
# ---------------------------------------------------------------------------


@router.post("/request", response_model=PrivacyRequestResponse)
async def create_privacy_request(
    firm_id: UUID,
    body: PrivacyRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    _membership=Depends(require_firm_member),
):
    """Create a data export or deletion request.

    Data export requests are auto-approved and processed immediately.
    Deletion requests require admin approval.
    """
    request_type = PrivacyRequestType(body.request_type)

    req = await privacy_service.create_request(
        db,
        firm_id=firm_id,
        user_id=current_user.user_id,
        request_type=request_type,
        reason=body.reason,
    )

    # Auto-approve and process data exports (no admin approval needed)
    if request_type == PrivacyRequestType.data_export:
        req = await privacy_service.review_request(
            db,
            request_id=req.id,
            firm_id=firm_id,
            action="approve",
            reviewer_id=current_user.user_id,
            note="Auto-approved: data export requests are processed immediately.",
        )

    await db.commit()
    return _to_response(req)


@router.get("/my-requests", response_model=list[PrivacyRequestResponse])
async def get_my_requests(
    firm_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    _membership=Depends(require_firm_member),
):
    """Get the current user's privacy requests."""
    requests = await privacy_service.list_my_requests(db, user_id=current_user.user_id)
    return [_to_response(r) for r in requests]


@router.get("/export", response_class=JSONResponse)
async def download_data_export(
    firm_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    _membership=Depends(require_firm_member),
):
    """Download a JSON export of all user data.

    Builds and returns the export immediately (synchronous).
    For large datasets, consider the async request workflow instead.
    """
    export_data = await privacy_service.build_data_export(
        db, user_id=current_user.user_id
    )
    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f'attachment; filename="data-export-{current_user.user_id}.json"',
        },
    )


# ---------------------------------------------------------------------------
# Admin endpoints (deletion approval queue)
# ---------------------------------------------------------------------------


@router.get("/admin/queue", response_model=PrivacyRequestListResponse)
async def list_privacy_requests(
    firm_id: UUID,
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    _membership=Depends(require_firm_member),
):
    """List all privacy requests for the firm (admin only)."""
    # Check admin role
    membership = next(
        (m for m in current_user.firm_memberships if str(m.firm_id) == str(firm_id)),
        None,
    )
    if not membership or membership.firm_role not in ("owner", "admin"):
        from app.core.exceptions import PermissionDeniedError
        raise PermissionDeniedError(detail="Admin access required")

    status_enum = PrivacyRequestStatus(status) if status else None
    requests, total = await privacy_service.list_requests(
        db, firm_id=firm_id, status=status_enum, page=page, per_page=per_page
    )

    return PrivacyRequestListResponse(
        data=[_to_response(r) for r in requests],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/admin/{request_id}/review", response_model=PrivacyRequestResponse)
async def review_privacy_request(
    firm_id: UUID,
    request_id: UUID,
    body: PrivacyRequestReview,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    _membership=Depends(require_firm_member),
):
    """Approve or reject a privacy request (admin only).

    Approved deletion requests will be queued for async processing.
    """
    membership = next(
        (m for m in current_user.firm_memberships if str(m.firm_id) == str(firm_id)),
        None,
    )
    if not membership or membership.firm_role not in ("owner", "admin"):
        from app.core.exceptions import PermissionDeniedError
        raise PermissionDeniedError(detail="Admin access required")

    req = await privacy_service.review_request(
        db,
        request_id=request_id,
        firm_id=firm_id,
        action=body.action,
        reviewer_id=current_user.user_id,
        note=body.note,
    )

    # If approved deletion, queue the async processing task
    if body.action == "approve" and req.request_type == PrivacyRequestType.data_deletion:
        try:
            from app.workers.privacy_tasks import process_deletion_request
            process_deletion_request.delay(str(request_id))
        except Exception:
            # Worker may not be running — deletion can be processed manually
            pass

    await db.commit()
    return _to_response(req)
