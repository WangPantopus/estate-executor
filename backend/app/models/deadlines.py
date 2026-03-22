from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import DeadlineSource, DeadlineStatus

if TYPE_CHECKING:
    from app.models.matters import Matter
    from app.models.stakeholders import Stakeholder
    from app.models.tasks import Task


class Deadline(BaseModel):
    __table_args__ = (
        Index(
            "ix_deadlines_matter_id_due_date_upcoming",
            "matter_id",
            "due_date",
            postgresql_where=text("status = 'upcoming'"),
        ),
    )

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[DeadlineSource] = mapped_column(
        Enum(DeadlineSource, name="deadline_source", native_enum=True),
        nullable=False,
    )
    rule: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[DeadlineStatus] = mapped_column(
        Enum(DeadlineStatus, name="deadline_status", native_enum=True),
        nullable=False,
        server_default="upcoming",
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stakeholders.id", ondelete="SET NULL"),
        nullable=True,
    )
    reminder_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default='{"days_before": [30, 7, 1]}',
    )
    last_reminder_sent: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    matter: Mapped[Matter] = relationship(back_populates="deadlines")
    task: Mapped[Task | None] = relationship(foreign_keys=[task_id])
    assignee: Mapped[Stakeholder | None] = relationship(foreign_keys=[assigned_to])
