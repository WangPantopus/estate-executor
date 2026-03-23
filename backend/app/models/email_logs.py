"""EmailLog model — tracks all outbound emails (body excluded for PII safety)."""

import uuid
from datetime import datetime

from sqlalchemy import Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    to_address: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    template: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    resend_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
