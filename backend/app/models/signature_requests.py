"""SignatureRequest model — tracks DocuSign envelopes sent for e-signature."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import SignatureRequestStatus, SignatureRequestType

if TYPE_CHECKING:
    from app.models.documents import Document
    from app.models.matters import Matter
    from app.models.stakeholders import Stakeholder


class SignatureRequest(BaseModel):
    __table_args__ = (
        Index("ix_signature_requests_matter_id", "matter_id"),
        Index("ix_signature_requests_envelope_id", "envelope_id"),
    )

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_type: Mapped[SignatureRequestType] = mapped_column(
        Enum(SignatureRequestType, name="signature_request_type", native_enum=True),
        nullable=False,
        server_default="general",
    )
    status: Mapped[SignatureRequestStatus] = mapped_column(
        Enum(SignatureRequestStatus, name="signature_request_status", native_enum=True),
        nullable=False,
        server_default="draft",
    )

    # DocuSign envelope info
    envelope_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    envelope_uri: Mapped[str | None] = mapped_column(String, nullable=True)

    # Request details
    subject: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stakeholders.id", ondelete="SET NULL"),
        nullable=False,
    )

    # Signers (stored as JSONB array of signer objects)
    signers: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )

    # Timestamps
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Signed document tracking
    signed_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )

    # Relationships
    matter: Mapped[Matter] = relationship()
    document: Mapped[Document | None] = relationship(foreign_keys=[document_id])
    sender: Mapped[Stakeholder] = relationship(foreign_keys=[sent_by])
