"""Document schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
    ai_extracted_data: dict | None
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
