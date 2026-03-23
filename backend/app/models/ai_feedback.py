"""AI feedback model — stores user corrections to AI outputs for future improvement."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AIFeedback(Base):
    """Immutable log of user corrections to AI outputs.

    Captures the original AI prediction, the user's correction, and context
    for future prompt improvement or fine-tuning.
    """

    __tablename__ = "ai_feedback"
    __table_args__ = (
        Index("ix_ai_feedback_firm_id_created_at", "firm_id", "created_at"),
        Index("ix_ai_feedback_feedback_type", "feedback_type"),
        Index("ix_ai_feedback_entity_id", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    matter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # "document", "asset", etc.
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    feedback_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # "classification_correction", "extraction_correction"
    ai_output: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=False
    )  # Original AI prediction
    user_correction: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=False
    )  # What the user changed it to
    corrected_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    model_used: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
