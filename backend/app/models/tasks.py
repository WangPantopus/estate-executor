from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import TaskPhase, TaskPriority, TaskStatus

if TYPE_CHECKING:
    from app.models.documents import Document
    from app.models.matters import Matter
    from app.models.stakeholders import Stakeholder
    from app.models.task_comments import TaskComment
    from app.models.task_dependencies import TaskDependency


class Task(BaseModel):
    __table_args__ = (
        Index("ix_tasks_matter_id_status", "matter_id", "status"),
        Index("ix_tasks_matter_id_phase", "matter_id", "phase"),
    )

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
    )
    template_key: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    instructions: Mapped[str | None] = mapped_column(String, nullable=True)
    phase: Mapped[TaskPhase] = mapped_column(
        Enum(TaskPhase, name="task_phase", native_enum=True),
        nullable=False,
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", native_enum=True),
        nullable=False,
        server_default="not_started",
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority", native_enum=True),
        nullable=False,
        server_default="normal",
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stakeholders.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date_rule: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    requires_document: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    completed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stakeholders.id", ondelete="SET NULL"),
        nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")

    matter: Mapped[Matter] = relationship(back_populates="tasks")
    parent_task: Mapped[Task | None] = relationship(
        remote_side="Task.id", back_populates="subtasks"
    )
    subtasks: Mapped[list[Task]] = relationship(back_populates="parent_task")
    assignee: Mapped[Stakeholder | None] = relationship(foreign_keys=[assigned_to])
    completer: Mapped[Stakeholder | None] = relationship(foreign_keys=[completed_by])
    dependencies: Mapped[list[TaskDependency]] = relationship(
        foreign_keys="[TaskDependency.task_id]",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    dependents: Mapped[list[TaskDependency]] = relationship(
        foreign_keys="[TaskDependency.depends_on_task_id]",
        back_populates="depends_on_task",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list[Document]] = relationship(
        secondary="task_documents", back_populates="tasks"
    )
    comments: Mapped[list[TaskComment]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
