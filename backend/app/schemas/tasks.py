"""Task schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import TaskPhase, TaskPriority, TaskStatus

from .common import PaginationMeta


class DocumentBrief(BaseModel):
    """Brief document reference for task responses."""

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "filename": "death_certificate.pdf",
                    "doc_type": "death_certificate",
                    "created_at": "2025-01-15T10:30:00Z",
                }
            ]
        },
    )

    id: UUID
    filename: str
    doc_type: str | None
    created_at: datetime


class CommentBrief(BaseModel):
    """Brief comment for task detail responses."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    author_id: UUID
    body: str
    created_at: datetime


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "Obtain Death Certificate",
                    "description": "Order certified copies of the death certificate",
                    "instructions": "Contact the county clerk to order copies.",
                    "phase": "immediate",
                    "priority": "critical",
                    "due_date": "2025-02-01",
                    "requires_document": True,
                }
            ]
        },
    )

    title: str
    description: str | None = None
    instructions: str | None = None
    phase: TaskPhase
    priority: TaskPriority | None = None
    assigned_to: UUID | None = None
    due_date: date | None = None
    requires_document: bool | None = None
    parent_task_id: UUID | None = None
    dependency_ids: list[UUID] | None = None


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "Obtain Death Certificate (Updated)",
                    "status": "in_progress",
                    "priority": "critical",
                    "sort_order": 1,
                }
            ]
        },
    )

    title: str | None = None
    description: str | None = None
    instructions: str | None = None
    phase: TaskPhase | None = None
    priority: TaskPriority | None = None
    assigned_to: UUID | None = None
    due_date: date | None = None
    status: TaskStatus | None = None
    sort_order: int | None = None


class TaskComplete(BaseModel):
    """Schema for completing a task."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "notes": "Death certificate received and filed.",
                }
            ]
        },
    )

    notes: str | None = None


class TaskWaive(BaseModel):
    """Schema for waiving a task."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "reason": "Not applicable to this estate type.",
                }
            ]
        },
    )

    reason: str


class TaskResponse(BaseModel):
    """Schema for task response."""

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "matter_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "parent_task_id": None,
                    "template_key": "obtain_death_certificate",
                    "title": "Obtain Death Certificate",
                    "description": "Order certified copies",
                    "instructions": "Contact the county clerk.",
                    "phase": "immediate",
                    "status": "not_started",
                    "priority": "critical",
                    "assigned_to": None,
                    "due_date": "2025-02-01",
                    "requires_document": True,
                    "completed_at": None,
                    "completed_by": None,
                    "sort_order": 0,
                    "metadata": {},
                    "documents": [],
                    "dependencies": [],
                    "created_at": "2025-01-15T10:30:00Z",
                    "updated_at": "2025-01-15T10:30:00Z",
                }
            ]
        },
    )

    id: UUID
    matter_id: UUID
    parent_task_id: UUID | None
    template_key: str | None
    title: str
    description: str | None
    instructions: str | None
    phase: TaskPhase
    status: TaskStatus
    priority: TaskPriority
    assigned_to: UUID | None
    due_date: date | None
    requires_document: bool
    completed_at: datetime | None
    completed_by: UUID | None
    sort_order: int
    metadata: dict[str, Any] | None
    documents: list[DocumentBrief]
    dependencies: list[UUID]
    created_at: datetime
    updated_at: datetime


class TaskListItem(BaseModel):
    """Task item for list responses — includes document count and dependency IDs."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    matter_id: UUID
    parent_task_id: UUID | None
    template_key: str | None
    title: str
    description: str | None
    instructions: str | None
    phase: TaskPhase
    status: TaskStatus
    priority: TaskPriority
    assigned_to: UUID | None
    due_date: date | None
    requires_document: bool
    completed_at: datetime | None
    completed_by: UUID | None
    sort_order: int
    metadata: dict[str, Any] | None
    document_count: int
    dependency_ids: list[UUID]
    created_at: datetime
    updated_at: datetime


class TaskDetailResponse(BaseModel):
    """Full task detail — includes documents, dependencies, dependents, and comments."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    matter_id: UUID
    parent_task_id: UUID | None
    template_key: str | None
    title: str
    description: str | None
    instructions: str | None
    phase: TaskPhase
    status: TaskStatus
    priority: TaskPriority
    assigned_to: UUID | None
    due_date: date | None
    requires_document: bool
    completed_at: datetime | None
    completed_by: UUID | None
    sort_order: int
    metadata: dict[str, Any] | None
    documents: list[DocumentBrief]
    dependencies: list[UUID]
    dependents: list[UUID]
    comments: list[CommentBrief]
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """Paginated list of tasks."""

    model_config = ConfigDict(strict=True)

    data: list[TaskListItem]
    meta: PaginationMeta


class TaskAssign(BaseModel):
    """Schema for assigning a task."""

    model_config = ConfigDict(strict=True)

    stakeholder_id: UUID


class TaskLinkDocument(BaseModel):
    """Schema for linking a document to a task."""

    model_config = ConfigDict(strict=True)

    document_id: UUID


class TaskGenerateRequest(BaseModel):
    """Schema for triggering task generation."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "regenerate": False,
                }
            ]
        },
    )

    regenerate: bool | None = None
