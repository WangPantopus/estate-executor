"""TimeEntry model — lightweight time tracking for professionals."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.matters import Matter
    from app.models.stakeholders import Stakeholder
    from app.models.tasks import Task


class TimeEntry(BaseModel):
    __table_args__ = (
        Index("ix_time_entries_matter_id", "matter_id"),
        Index("ix_time_entries_task_id", "task_id"),
        Index("ix_time_entries_stakeholder_id", "stakeholder_id"),
        Index("ix_time_entries_entry_date", "entry_date"),
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
    stakeholder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stakeholders.id", ondelete="CASCADE"),
        nullable=False,
    )
    hours: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    description: Mapped[str] = mapped_column(String, nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    billable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    # Relationships
    matter: Mapped[Matter] = relationship()
    task: Mapped[Task | None] = relationship()
    stakeholder: Mapped[Stakeholder] = relationship()
