from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.assets import Asset
    from app.models.document_versions import DocumentVersion
    from app.models.matters import Matter
    from app.models.stakeholders import Stakeholder
    from app.models.tasks import Task


class Document(BaseModel):
    __table_args__ = (Index("ix_documents_matter_id_doc_type", "matter_id", "doc_type"),)

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stakeholders.id", ondelete="SET NULL"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    doc_type: Mapped[str | None] = mapped_column(String, nullable=True)
    doc_type_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    doc_type_confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    ai_extracted_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    matter: Mapped[Matter] = relationship(back_populates="documents")
    uploader: Mapped[Stakeholder] = relationship(foreign_keys=[uploaded_by])
    versions: Mapped[list[DocumentVersion]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    tasks: Mapped[list[Task]] = relationship(secondary="task_documents", back_populates="documents")
    assets: Mapped[list[Asset]] = relationship(
        secondary="asset_documents", back_populates="documents"
    )
