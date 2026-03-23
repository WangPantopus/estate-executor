"""Document upload & management API routes."""

from __future__ import annotations

import math
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.security import get_current_user, require_firm_member, require_stakeholder
from app.models.documents import Document
from app.models.enums import StakeholderRole
from app.models.firm_memberships import FirmMembership
from app.models.stakeholders import Stakeholder
from app.schemas.auth import CurrentUser
from app.schemas.common import PaginationMeta, PaginationParams
from app.schemas.documents import (
    AssetBriefDoc,
    BulkDownloadRequest,
    BulkDownloadStatusResponse,
    DocumentConfirmType,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentRegister,
    DocumentRequestCreate,
    DocumentResponse,
    DocumentUploadRequest,
    DocumentUploadURL,
    DocumentVersionResponse,
    DownloadURLResponse,
    RegisterVersionRequest,
    TaskBriefDoc,
)
from app.services import document_service

router = APIRouter()

# Roles that can upload/modify documents
_UPLOAD_ROLES = {
    StakeholderRole.matter_admin,
    StakeholderRole.professional,
    StakeholderRole.executor_trustee,
}

# Roles that can read documents
_READ_ROLES = {
    StakeholderRole.matter_admin,
    StakeholderRole.professional,
    StakeholderRole.executor_trustee,
    StakeholderRole.beneficiary,
}


def _require_doc_read(stakeholder: Stakeholder) -> None:
    """Raise NotFoundError if role cannot read documents."""
    if stakeholder.role not in _READ_ROLES:
        raise NotFoundError(detail="Documents not found")


def _require_doc_upload(stakeholder: Stakeholder) -> None:
    """Raise PermissionDeniedError if role cannot upload documents."""
    if stakeholder.role not in _UPLOAD_ROLES:
        raise PermissionDeniedError(detail="Insufficient permissions")


def _require_doc_admin(stakeholder: Stakeholder) -> None:
    """Raise PermissionDeniedError if role cannot admin documents."""
    if stakeholder.role not in {StakeholderRole.matter_admin, StakeholderRole.professional}:
        raise PermissionDeniedError(detail="Insufficient permissions")


def _doc_to_response(doc: Document) -> DocumentResponse:
    """Convert a Document ORM object to DocumentResponse."""
    return DocumentResponse(
        id=doc.id,
        matter_id=doc.matter_id,
        uploaded_by=doc.uploaded_by,
        filename=doc.filename,
        storage_key=doc.storage_key,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        doc_type=doc.doc_type,
        doc_type_confidence=doc.doc_type_confidence,
        doc_type_confirmed=doc.doc_type_confirmed,
        ai_extracted_data=doc.ai_extracted_data,
        current_version=doc.current_version,
        created_at=doc.created_at,
    )


def _doc_to_detail(doc: Document) -> DocumentDetailResponse:
    """Convert a Document ORM object to full detail response."""
    versions = [
        DocumentVersionResponse(
            id=v.id,
            document_id=v.document_id,
            version_number=v.version_number,
            storage_key=v.storage_key,
            size_bytes=v.size_bytes,
            uploaded_by=v.uploaded_by,
            created_at=v.created_at,
        )
        for v in sorted(doc.versions, key=lambda v: v.version_number)
    ]
    linked_tasks = [TaskBriefDoc(id=t.id, title=t.title) for t in doc.tasks]
    linked_assets = [AssetBriefDoc(id=a.id, title=a.title) for a in doc.assets]
    return DocumentDetailResponse(
        id=doc.id,
        matter_id=doc.matter_id,
        uploaded_by=doc.uploaded_by,
        filename=doc.filename,
        storage_key=doc.storage_key,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        doc_type=doc.doc_type,
        doc_type_confidence=doc.doc_type_confidence,
        doc_type_confirmed=doc.doc_type_confirmed,
        ai_extracted_data=doc.ai_extracted_data,
        current_version=doc.current_version,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        versions=versions,
        linked_tasks=linked_tasks,
        linked_assets=linked_assets,
    )


# ---------------------------------------------------------------------------
# POST .../documents/upload-url — Get presigned upload URL
# ---------------------------------------------------------------------------


@router.post("/upload-url", response_model=DocumentUploadURL, status_code=200)
async def get_upload_url(
    firm_id: UUID,
    matter_id: UUID,
    body: DocumentUploadRequest,
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
) -> DocumentUploadURL:
    """Get a presigned S3 upload URL for direct browser upload.

    Requires at least executor_trustee role (beneficiary/read_only blocked).
    """
    _require_doc_upload(_stakeholder)
    upload_url, storage_key, expires_in = document_service.get_upload_url(
        firm_id=firm_id,
        matter_id=matter_id,
        filename=body.filename,
        mime_type=body.mime_type,
    )
    return DocumentUploadURL(
        upload_url=upload_url,
        storage_key=storage_key,
        expires_in=expires_in,
    )


# ---------------------------------------------------------------------------
# POST .../documents — Register document after upload
# ---------------------------------------------------------------------------


@router.post("", response_model=DocumentDetailResponse, status_code=201)
async def register_document(
    firm_id: UUID,
    matter_id: UUID,
    body: DocumentRegister,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    """Register a document after successful S3 upload."""
    _require_doc_upload(stakeholder)
    doc = await document_service.register_document(
        db,
        matter_id=matter_id,
        stakeholder=stakeholder,
        filename=body.filename,
        storage_key=body.storage_key,
        mime_type=body.mime_type,
        size_bytes=body.size_bytes,
        task_id=body.task_id,
        asset_id=body.asset_id,
        current_user=current_user,
    )
    return _doc_to_detail(doc)


# ---------------------------------------------------------------------------
# GET .../documents — List documents
# ---------------------------------------------------------------------------


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    firm_id: UUID,
    matter_id: UUID,
    doc_type: str | None = Query(None),
    doc_type_confirmed: bool | None = Query(None),
    linked_task_id: UUID | None = Query(None),
    linked_asset_id: UUID | None = Query(None),
    search: str | None = Query(None),
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """List documents with filters and pagination.

    read_only role cannot access documents at all.
    """
    _require_doc_read(_stakeholder)
    docs, total = await document_service.list_documents(
        db,
        matter_id=matter_id,
        doc_type=doc_type,
        doc_type_confirmed=doc_type_confirmed,
        linked_task_id=linked_task_id,
        linked_asset_id=linked_asset_id,
        search=search,
        page=pagination.page,
        per_page=pagination.per_page,
    )
    return DocumentListResponse(
        data=[_doc_to_response(d) for d in docs],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0,
        ),
    )


# ---------------------------------------------------------------------------
# POST .../documents/request — Request document from stakeholder
# (must be before /{doc_id} routes to avoid path conflict)
# ---------------------------------------------------------------------------


@router.post("/request", status_code=201)
async def request_document(
    firm_id: UUID,
    matter_id: UUID,
    body: DocumentRequestCreate,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Request a document from a stakeholder. Sends email with upload link."""
    _require_doc_admin(stakeholder)
    comm = await document_service.request_document(
        db,
        matter_id=matter_id,
        sender=stakeholder,
        target_stakeholder_id=body.target_stakeholder_id,
        doc_type_needed=body.doc_type_needed,
        task_id=body.task_id,
        message=body.message,
        current_user=current_user,
    )
    return {"id": str(comm.id), "status": "sent"}


# ---------------------------------------------------------------------------
# POST .../documents/bulk-download — Enqueue bulk download
# (must be before /{doc_id} routes to avoid path conflict)
# ---------------------------------------------------------------------------


@router.post("/bulk-download", response_model=BulkDownloadStatusResponse, status_code=202)
async def bulk_download(
    firm_id: UUID,
    matter_id: UUID,
    body: BulkDownloadRequest,
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BulkDownloadStatusResponse:
    """Enqueue async ZIP generation for bulk document download."""
    _require_doc_read(_stakeholder)
    job_id = await document_service.enqueue_bulk_download(
        db,
        matter_id=matter_id,
        document_ids=body.document_ids,
        current_user=current_user,
    )
    return BulkDownloadStatusResponse(job_id=job_id, status="processing")


# ---------------------------------------------------------------------------
# GET .../documents/bulk-download/{job_id} — Check bulk download status
# (must be before /{doc_id} routes to avoid path conflict)
# ---------------------------------------------------------------------------


@router.get("/bulk-download/{job_id}", response_model=BulkDownloadStatusResponse)
async def bulk_download_status(
    firm_id: UUID,
    matter_id: UUID,
    job_id: str,
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
) -> BulkDownloadStatusResponse:
    """Check status of a bulk download ZIP generation job."""
    _require_doc_read(_stakeholder)
    from app.workers.celery_app import celery_app

    result = celery_app.AsyncResult(job_id)

    if result.ready():
        if result.successful():
            data = result.result
            return BulkDownloadStatusResponse(
                job_id=job_id,
                status="completed",
                download_url=data.get("download_url") if isinstance(data, dict) else None,
            )
        return BulkDownloadStatusResponse(job_id=job_id, status="failed")

    return BulkDownloadStatusResponse(job_id=job_id, status="processing")


# ---------------------------------------------------------------------------
# GET .../documents/{doc_id} — Document detail
# (parameterized routes MUST come after all fixed-path routes)
# ---------------------------------------------------------------------------


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(
    firm_id: UUID,
    matter_id: UUID,
    doc_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    """Get full document detail with versions, linked tasks, and linked assets."""
    _require_doc_read(_stakeholder)
    doc = await document_service.get_document(db, doc_id=doc_id, matter_id=matter_id)
    return _doc_to_detail(doc)


# ---------------------------------------------------------------------------
# GET .../documents/{doc_id}/download — Get presigned download URL
# ---------------------------------------------------------------------------


@router.get("/{doc_id}/download", response_model=DownloadURLResponse)
async def get_download_url(
    firm_id: UUID,
    matter_id: UUID,
    doc_id: UUID,
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DownloadURLResponse:
    """Get a presigned download URL. Access is logged for audit."""
    _require_doc_read(_stakeholder)
    download_url, expires_in = await document_service.get_download_url(
        db, doc_id=doc_id, matter_id=matter_id, current_user=current_user
    )
    return DownloadURLResponse(download_url=download_url, expires_in=expires_in)


# ---------------------------------------------------------------------------
# POST .../documents/{doc_id}/confirm-type — Confirm AI classification
# ---------------------------------------------------------------------------


@router.post("/{doc_id}/confirm-type", response_model=DocumentResponse)
async def confirm_doc_type(
    firm_id: UUID,
    matter_id: UUID,
    doc_id: UUID,
    body: DocumentConfirmType,
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Confirm or override the AI-classified document type."""
    _require_doc_admin(_stakeholder)
    doc = await document_service.confirm_doc_type(
        db, doc_id=doc_id, matter_id=matter_id, doc_type=body.doc_type, current_user=current_user
    )
    return _doc_to_response(doc)


# ---------------------------------------------------------------------------
# POST .../documents/{doc_id}/reupload — Get upload URL for new version
# ---------------------------------------------------------------------------


@router.post("/{doc_id}/reupload", response_model=DocumentUploadURL)
async def reupload_document(
    firm_id: UUID,
    matter_id: UUID,
    doc_id: UUID,
    body: DocumentUploadRequest,
    _membership: FirmMembership = Depends(require_firm_member),
    _stakeholder: Stakeholder = Depends(require_stakeholder),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadURL:
    """Get a presigned upload URL for uploading a new version."""
    _require_doc_upload(_stakeholder)
    # Verify doc exists
    await document_service.get_document(db, doc_id=doc_id, matter_id=matter_id)

    upload_url, storage_key, expires_in = document_service.get_reupload_url(
        firm_id=firm_id,
        matter_id=matter_id,
        doc_id=doc_id,
        filename=body.filename,
        mime_type=body.mime_type,
    )
    return DocumentUploadURL(
        upload_url=upload_url,
        storage_key=storage_key,
        expires_in=expires_in,
    )


# ---------------------------------------------------------------------------
# POST .../documents/{doc_id}/version — Register new version
# ---------------------------------------------------------------------------


@router.post("/{doc_id}/version", response_model=DocumentDetailResponse, status_code=201)
async def register_version(
    firm_id: UUID,
    matter_id: UUID,
    doc_id: UUID,
    body: RegisterVersionRequest,
    _membership: FirmMembership = Depends(require_firm_member),
    stakeholder: Stakeholder = Depends(require_stakeholder),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    """Register a new version for an existing document."""
    _require_doc_upload(stakeholder)
    doc = await document_service.register_version(
        db,
        doc_id=doc_id,
        matter_id=matter_id,
        stakeholder=stakeholder,
        storage_key=body.storage_key,
        size_bytes=body.size_bytes,
        current_user=current_user,
    )
    return _doc_to_detail(doc)
