"""DocumentRequest model — tracks token-based document upload requests."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import DocumentRequestStatus

if TYPE_CHECKING:
    from app.models.documents import Document
    from app.models.matters import Matter
    from app.models.stakeholders import Stakeholder
    from app.models.tasks import Task


def _generate_upload_token() -> str:
    """Generate a URL-safe upload token (48 chars)."""
    return secrets.token_urlsafe(36)


class DocumentRequest(BaseModel):
    __table_args__ = (
        Index("ix_document_requests_token", "upload_token", unique=True),
        Index("ix_document_requests_matter_id", "matter_id"),
        Index("ix_document_requests_status", "status"),
    )

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
    )
    requester_stakeholder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stakeholders.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_stakeholder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stakeholders.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    doc_type_needed: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str | None] = mapped_column(String, nullable=True)
    upload_token: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, default=_generate_upload_token
    )
    status: Mapped[DocumentRequestStatus] = mapped_column(
        Enum(DocumentRequestStatus, name="document_request_status", native_enum=True),
        nullable=False,
        server_default="pending",
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Relationships
    matter: Mapped[Matter] = relationship()
    requester: Mapped[Stakeholder] = relationship(
        foreign_keys=[requester_stakeholder_id]
    )
    target: Mapped[Stakeholder] = relationship(
        foreign_keys=[target_stakeholder_id]
    )
    task: Mapped[Task | None] = relationship()
    document: Mapped[Document | None] = relationship()
