"""Document business logic — upload flow, registration, versioning, linking."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.events import event_logger
from app.core.exceptions import NotFoundError
from app.models.asset_documents import asset_documents
from app.models.communications import Communication
from app.models.document_versions import DocumentVersion
from app.models.documents import Document
from app.models.enums import ActorType, CommunicationType, CommunicationVisibility
from app.models.stakeholders import Stakeholder
from app.models.task_documents import task_documents
from app.services import storage_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

_PRESIGN_EXPIRY = 900  # 15 minutes — matches storage_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_document_or_404(
    db: AsyncSession, *, doc_id: uuid.UUID, matter_id: uuid.UUID
) -> Document:
    result = await db.execute(
        select(Document)
        .options(
            selectinload(Document.versions),
            selectinload(Document.tasks),
            selectinload(Document.assets),
        )
        .where(Document.id == doc_id, Document.matter_id == matter_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFoundError(detail="Document not found")
    return doc


# ---------------------------------------------------------------------------
# Upload URL generation
# ---------------------------------------------------------------------------


def get_upload_url(
    *, firm_id: uuid.UUID, matter_id: uuid.UUID, filename: str, mime_type: str
) -> tuple[str, str, int]:
    """Generate presigned upload URL. Returns (upload_url, storage_key, expires_in)."""
    upload_url, storage_key = storage_service.generate_upload_url(
        firm_id=firm_id,
        matter_id=matter_id,
        filename=filename,
        mime_type=mime_type,
    )
    return upload_url, storage_key, _PRESIGN_EXPIRY


# ---------------------------------------------------------------------------
# Register document (after upload)
# ---------------------------------------------------------------------------


async def register_document(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    stakeholder: Stakeholder,
    filename: str,
    storage_key: str,
    mime_type: str,
    size_bytes: int,
    task_id: uuid.UUID | None = None,
    asset_id: uuid.UUID | None = None,
    current_user: CurrentUser,
) -> Document:
    """Register a document after successful S3 upload."""
    doc = Document(
        matter_id=matter_id,
        uploaded_by=stakeholder.id,
        filename=filename,
        storage_key=storage_key,
        mime_type=mime_type,
        size_bytes=size_bytes,
    )
    db.add(doc)
    await db.flush()

    # Create initial version record
    v1 = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        storage_key=storage_key,
        size_bytes=size_bytes,
        uploaded_by=stakeholder.id,
    )
    db.add(v1)

    # Link to task if provided
    if task_id is not None:
        await db.execute(task_documents.insert().values(task_id=task_id, document_id=doc.id))

    # Link to asset if provided
    if asset_id is not None:
        await db.execute(asset_documents.insert().values(asset_id=asset_id, document_id=doc.id))

    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="document",
        entity_id=doc.id,
        action="uploaded",
        metadata={
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "task_id": str(task_id) if task_id else None,
            "asset_id": str(asset_id) if asset_id else None,
        },
    )

    # Enqueue AI classification (Celery task — import at call site to avoid circular)
    from app.workers.ai_tasks import classify_document

    classify_document.delay(str(doc.id), str(matter_id))

    return await _get_document_or_404(db, doc_id=doc.id, matter_id=matter_id)


# ---------------------------------------------------------------------------
# List documents
# ---------------------------------------------------------------------------


async def list_documents(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    doc_type: str | None = None,
    doc_type_confirmed: bool | None = None,
    linked_task_id: uuid.UUID | None = None,
    linked_asset_id: uuid.UUID | None = None,
    search: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[Document], int]:
    """List documents with filters and pagination."""
    filters: list[Any] = [Document.matter_id == matter_id]

    if doc_type is not None:
        filters.append(Document.doc_type == doc_type)
    if doc_type_confirmed is not None:
        filters.append(Document.doc_type_confirmed == doc_type_confirmed)
    if search is not None:
        filters.append(Document.filename.ilike(f"%{search}%"))

    # Junction table filters
    q_base = select(Document).where(*filters)

    if linked_task_id is not None:
        q_base = q_base.join(task_documents).where(task_documents.c.task_id == linked_task_id)
    if linked_asset_id is not None:
        q_base = q_base.join(asset_documents).where(asset_documents.c.asset_id == linked_asset_id)

    # Count
    count_q = select(func.count()).select_from(q_base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Data
    q = q_base.order_by(Document.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    docs = list(result.scalars().unique().all())

    return docs, total


# ---------------------------------------------------------------------------
# Get document detail
# ---------------------------------------------------------------------------


async def get_document(db: AsyncSession, *, doc_id: uuid.UUID, matter_id: uuid.UUID) -> Document:
    """Get full document detail with versions, tasks, and assets."""
    return await _get_document_or_404(db, doc_id=doc_id, matter_id=matter_id)


# ---------------------------------------------------------------------------
# Download URL
# ---------------------------------------------------------------------------


async def get_download_url(
    db: AsyncSession,
    *,
    doc_id: uuid.UUID,
    matter_id: uuid.UUID,
    current_user: CurrentUser,
) -> tuple[str, int]:
    """Generate a presigned download URL and log access."""
    doc = await _get_document_or_404(db, doc_id=doc_id, matter_id=matter_id)

    download_url = storage_service.generate_download_url(storage_key=doc.storage_key)

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="document",
        entity_id=doc.id,
        action="downloaded",
        metadata={"filename": doc.filename},
    )

    return download_url, _PRESIGN_EXPIRY


# ---------------------------------------------------------------------------
# Confirm AI classification
# ---------------------------------------------------------------------------


async def confirm_doc_type(
    db: AsyncSession,
    *,
    doc_id: uuid.UUID,
    matter_id: uuid.UUID,
    doc_type: str,
    current_user: CurrentUser,
) -> Document:
    """Confirm or override the AI-classified document type."""
    doc = await _get_document_or_404(db, doc_id=doc_id, matter_id=matter_id)

    old_type = doc.doc_type
    old_confidence = doc.doc_type_confidence
    doc.doc_type = doc_type
    doc.doc_type_confirmed = True
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="document",
        entity_id=doc.id,
        action="type_confirmed",
        changes={"doc_type": {"old": old_type, "new": doc_type}},
    )

    # Log AI feedback for classification correction/confirmation
    try:
        from app.services.ai_feedback_service import log_classification_correction

        await log_classification_correction(
            db,
            firm_id=current_user.firm_id,
            matter_id=matter_id,
            document_id=doc.id,
            original_doc_type=old_type,
            original_confidence=old_confidence,
            corrected_doc_type=doc_type,
            corrected_by=current_user.user_id,
        )
    except Exception:
        logger.warning("Failed to log AI feedback for classification", exc_info=True)

    return doc


# ---------------------------------------------------------------------------
# Reupload (new version upload URL)
# ---------------------------------------------------------------------------


def get_reupload_url(
    *,
    firm_id: uuid.UUID,
    matter_id: uuid.UUID,
    doc_id: uuid.UUID,
    filename: str,
    mime_type: str,
) -> tuple[str, str, int]:
    """Generate presigned upload URL for a new version of a document."""
    version_uuid = uuid.uuid4()
    storage_key = (
        f"firms/{firm_id}/matters/{matter_id}/documents/{doc_id}/v/{version_uuid}/{filename}"
    )

    from app.services.storage_service import _get_s3_client

    client = _get_s3_client()
    upload_url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.aws_s3_bucket,
            "Key": storage_key,
            "ContentType": mime_type,
        },
        ExpiresIn=_PRESIGN_EXPIRY,
    )
    return upload_url, storage_key, _PRESIGN_EXPIRY


# ---------------------------------------------------------------------------
# Register new version
# ---------------------------------------------------------------------------


async def register_version(
    db: AsyncSession,
    *,
    doc_id: uuid.UUID,
    matter_id: uuid.UUID,
    stakeholder: Stakeholder,
    storage_key: str,
    size_bytes: int,
    current_user: CurrentUser,
) -> Document:
    """Register a new version for an existing document."""
    doc = await _get_document_or_404(db, doc_id=doc_id, matter_id=matter_id)

    new_version = doc.current_version + 1
    doc.current_version = new_version
    doc.storage_key = storage_key
    doc.size_bytes = size_bytes

    version = DocumentVersion(
        document_id=doc.id,
        version_number=new_version,
        storage_key=storage_key,
        size_bytes=size_bytes,
        uploaded_by=stakeholder.id,
    )
    db.add(version)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="document",
        entity_id=doc.id,
        action="version_uploaded",
        metadata={
            "version_number": new_version,
            "storage_key": storage_key,
            "size_bytes": size_bytes,
        },
    )

    return await _get_document_or_404(db, doc_id=doc_id, matter_id=matter_id)


# ---------------------------------------------------------------------------
# Request document from stakeholder
# ---------------------------------------------------------------------------


async def request_document(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    sender: Stakeholder,
    target_stakeholder_id: uuid.UUID,
    doc_type_needed: str,
    task_id: uuid.UUID | None = None,
    message: str | None = None,
    current_user: CurrentUser,
) -> Communication:
    """Create a document request communication to a stakeholder."""
    body = message or f"Please upload a {doc_type_needed} document."
    subject = f"Document Request: {doc_type_needed}"

    comm = Communication(
        matter_id=matter_id,
        sender_id=sender.id,
        type=CommunicationType.document_request,
        subject=subject,
        body=body,
        visibility=CommunicationVisibility.specific,
        visible_to=[sender.id, target_stakeholder_id],
        acknowledged_by=[],
    )
    db.add(comm)
    await db.flush()

    await event_logger.log(
        db,
        matter_id=matter_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.user,
        entity_type="communication",
        entity_id=comm.id,
        action="document_requested",
        metadata={
            "target_stakeholder_id": str(target_stakeholder_id),
            "doc_type_needed": doc_type_needed,
            "task_id": str(task_id) if task_id else None,
        },
    )

    # Email stub
    target = await db.execute(select(Stakeholder).where(Stakeholder.id == target_stakeholder_id))
    target_stakeholder = target.scalar_one_or_none()
    if target_stakeholder:
        logger.info(
            "document_request_email_stub",
            extra={
                "target_email": target_stakeholder.email,
                "target_name": target_stakeholder.full_name,
                "doc_type_needed": doc_type_needed,
            },
        )

    return comm


# ---------------------------------------------------------------------------
# Bulk download (enqueue ZIP generation)
# ---------------------------------------------------------------------------


async def enqueue_bulk_download(
    db: AsyncSession,
    *,
    matter_id: uuid.UUID,
    document_ids: list[uuid.UUID],
    current_user: CurrentUser,
) -> str:
    """Enqueue async ZIP generation job. Returns job_id."""
    from app.workers.document_tasks import generate_bulk_download

    job_id = str(uuid.uuid4())
    generate_bulk_download.delay(
        job_id,
        str(matter_id),
        [str(d) for d in document_ids],
        "",  # requester_stakeholder_id — populated by caller if needed
    )

    logger.info(
        "bulk_download_enqueued",
        extra={
            "job_id": job_id,
            "matter_id": str(matter_id),
            "document_count": len(document_ids),
        },
    )

    return job_id
