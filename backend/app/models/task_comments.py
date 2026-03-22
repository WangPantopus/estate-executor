from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.stakeholders import Stakeholder
    from app.models.tasks import Task


class TaskComment(BaseModel):
    __tablename__ = "task_comments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stakeholders.id", ondelete="SET NULL"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(String, nullable=False)

    task: Mapped[Task] = relationship(back_populates="comments")
    author: Mapped[Stakeholder] = relationship(foreign_keys=[author_id])
