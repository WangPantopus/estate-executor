"""Public document upload routes — token-based, no authentication required.

These routes power the lightweight standalone upload page that executors
receive via email when a professional requests a document.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.schemas.documents import (
    DocumentRequestInfo,
    DocumentUploadURL,
    TokenUploadComplete,
    TokenUploadRequest,
)
from app.services import document_service

router = APIRouter()


@router.get("/{token}", response_model=DocumentRequestInfo)
async def get_upload_info(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentRequestInfo:
    """Public endpoint: get document request info for the upload page.

    No authentication required — the token itself is the credential.
    """
    doc_request = await document_service.get_request_by_token(db, token=token)
    matter = doc_request.matter
    requester = doc_request.requester

    # Get firm name if available
    firm_name: str | None = None
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.models.matters import Matter

        matter_result = await db.execute(
            select(Matter).options(selectinload(Matter.firm)).where(Matter.id == matter.id)
        )
        matter_full = matter_result.scalar_one_or_none()
        if matter_full and matter_full.firm:
            firm_name = matter_full.firm.name
    except Exception:
        pass

    return DocumentRequestInfo(
        request_id=doc_request.id,
        matter_title=matter.title,
        decedent_name=matter.decedent_name,
        requester_name=requester.full_name,
        doc_type_needed=doc_request.doc_type_needed,
        message=doc_request.message,
        status=doc_request.status.value,
        expires_at=doc_request.expires_at,
        firm_name=firm_name,
    )


@router.post("/{token}/presign", response_model=DocumentUploadURL)
async def get_token_upload_url(
    token: str,
    body: TokenUploadRequest,
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadURL:
    """Public endpoint: get a presigned S3 upload URL using the request token."""
    doc_request = await document_service.get_request_by_token(db, token=token)

    upload_url, storage_key, expires_in = document_service.get_token_upload_url(
        matter=doc_request.matter,
        filename=body.filename,
        mime_type=body.mime_type,
    )
    return DocumentUploadURL(
        upload_url=upload_url,
        storage_key=storage_key,
        expires_in=expires_in,
    )


@router.post("/{token}/complete", status_code=201)
async def complete_token_upload(
    token: str,
    body: TokenUploadComplete,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Public endpoint: register document after upload via token link.

    This completes the flow:
    - Document is registered and linked to the requesting task
    - AI classification is enqueued
    - Professional who requested the document is notified
    """
    doc_request = await document_service.get_request_by_token(db, token=token)

    doc = await document_service.complete_token_upload(
        db,
        doc_request=doc_request,
        filename=body.filename,
        storage_key=body.storage_key,
        mime_type=body.mime_type,
        size_bytes=body.size_bytes,
    )
    return {
        "status": "uploaded",
        "document_id": str(doc.id),
        "filename": doc.filename,
    }
