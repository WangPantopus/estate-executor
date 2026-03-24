"""Document schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .common import PaginationMeta


class DocumentUploadRequest(BaseModel):
    """Input for requesting a presigned upload URL."""

    model_config = ConfigDict(strict=True)

    filename: str
    mime_type: str


class DocumentRegister(BaseModel):
    """Schema for registering a document after upload."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "filename": "death_certificate.pdf",
                    "storage_key": "matters/abc123/documents/death_certificate.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 204800,
                    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                }
            ]
        },
    )

    filename: str
    storage_key: str
    mime_type: str
    size_bytes: int
    task_id: UUID | None = None
    asset_id: UUID | None = None


class DocumentResponse(BaseModel):
    """Schema for document response."""

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "matter_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "uploaded_by": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                    "filename": "death_certificate.pdf",
                    "storage_key": "matters/abc123/documents/death_certificate.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 204800,
                    "doc_type": "death_certificate",
                    "doc_type_confidence": 0.95,
                    "doc_type_confirmed": True,
                    "ai_extracted_data": {"date_of_death": "2025-01-01"},
                    "current_version": 1,
                    "created_at": "2025-01-15T10:30:00Z",
                }
            ]
        },
    )

    id: UUID
    matter_id: UUID
    uploaded_by: UUID
    filename: str
    storage_key: str
    mime_type: str
    size_bytes: int
    doc_type: str | None
    doc_type_confidence: float | None
    doc_type_confirmed: bool
    ai_extracted_data: dict[str, Any] | None
    current_version: int
    created_at: datetime


class DocumentUploadURL(BaseModel):
    """Pre-signed upload URL response."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "upload_url": "https://storage.example.com/upload?token=abc",
                    "storage_key": "matters/abc123/documents/file.pdf",
                    "expires_in": 3600,
                }
            ]
        },
    )

    upload_url: str
    storage_key: str
    expires_in: int


class DocumentConfirmType(BaseModel):
    """Schema for confirming or overriding a document type classification."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "doc_type": "death_certificate",
                }
            ]
        },
    )

    doc_type: str


class DocumentRequestCreate(BaseModel):
    """Schema for creating a document request to a stakeholder."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "target_stakeholder_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "doc_type_needed": "bank_statement",
                    "task_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "message": "Please upload your most recent bank statement.",
                }
            ]
        },
    )

    target_stakeholder_id: UUID
    doc_type_needed: str
    task_id: UUID | None = None
    message: str | None = None


class DocumentVersionResponse(BaseModel):
    """Schema for a document version."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    document_id: UUID
    version_number: int
    storage_key: str
    size_bytes: int
    uploaded_by: UUID
    created_at: datetime


class TaskBriefDoc(BaseModel):
    """Brief task info linked to a document."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    title: str


class AssetBriefDoc(BaseModel):
    """Brief asset info linked to a document."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    title: str


class DocumentDetailResponse(BaseModel):
    """Full document detail with versions, linked tasks, and linked assets."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    matter_id: UUID
    uploaded_by: UUID
    filename: str
    storage_key: str
    mime_type: str
    size_bytes: int
    doc_type: str | None
    doc_type_confidence: float | None
    doc_type_confirmed: bool
    ai_extracted_data: dict[str, Any] | None
    current_version: int
    created_at: datetime
    updated_at: datetime
    versions: list[DocumentVersionResponse] = []
    linked_tasks: list[TaskBriefDoc] = []
    linked_assets: list[AssetBriefDoc] = []


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    model_config = ConfigDict(strict=True)

    data: list[DocumentResponse]
    meta: PaginationMeta


class DownloadURLResponse(BaseModel):
    """Presigned download URL."""

    model_config = ConfigDict(strict=True)

    download_url: str
    expires_in: int


class RegisterVersionRequest(BaseModel):
    """Input for registering a new document version after upload."""

    model_config = ConfigDict(strict=True)

    storage_key: str
    size_bytes: int


class BulkDownloadRequest(BaseModel):
    """Input for bulk download of documents."""

    model_config = ConfigDict(strict=True)

    document_ids: list[UUID]


class BulkDownloadStatusResponse(BaseModel):
    """Status of a bulk download job."""

    model_config = ConfigDict(strict=True)

    job_id: str
    status: str
    download_url: str | None = None


# ---------------------------------------------------------------------------
# Document Request (token-based upload flow)
# ---------------------------------------------------------------------------


class DocumentRequestResponse(BaseModel):
    """Response after creating a document request."""

    model_config = ConfigDict(strict=True)

    id: UUID
    upload_token: str
    upload_url: str
    status: str
    expires_at: datetime


class DocumentRequestInfo(BaseModel):
    """Public info returned when loading an upload page via token."""

    model_config = ConfigDict(strict=True)

    request_id: UUID
    matter_title: str
    decedent_name: str
    requester_name: str
    doc_type_needed: str
    message: str | None
    status: str
    expires_at: datetime
    firm_name: str | None = None


class TokenUploadRequest(BaseModel):
    """Input for requesting a presigned upload URL via token."""

    model_config = ConfigDict(strict=True)

    filename: str
    mime_type: str


class TokenUploadComplete(BaseModel):
    """Input for completing an upload via token."""

    model_config = ConfigDict(strict=True)

    filename: str
    storage_key: str
    mime_type: str
    size_bytes: int
