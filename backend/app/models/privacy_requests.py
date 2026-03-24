"""Privacy request model — tracks GDPR/CCPA data export and deletion requests."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import PrivacyRequestStatus, PrivacyRequestType

if TYPE_CHECKING:
    from datetime import datetime

    from app.models.users import User


class PrivacyRequest(BaseModel):
    __table_args__ = (
        Index("ix_privacy_requests_user_id_status", "user_id", "status"),
        Index("ix_privacy_requests_firm_id_status", "firm_id", "status"),
    )

    firm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    request_type: Mapped[PrivacyRequestType] = mapped_column(
        Enum(PrivacyRequestType, name="privacy_request_type", native_enum=True),
        nullable=False,
    )
    status: Mapped[PrivacyRequestStatus] = mapped_column(
        Enum(PrivacyRequestStatus, name="privacy_request_status", native_enum=True),
        nullable=False,
        server_default="pending",
    )
    reason: Mapped[str | None] = mapped_column(String, nullable=True)

    # Admin who approved/rejected
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(String, nullable=True)

    # Processing metadata
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    export_storage_key: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # S3 key for data export ZIP
    deletion_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )  # summary of what was anonymized

    # Relationships
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewed_by])
