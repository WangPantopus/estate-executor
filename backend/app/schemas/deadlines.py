"""Deadline schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import DeadlineSource, DeadlineStatus

from .common import PaginationMeta


class DeadlineCreate(BaseModel):
    """Schema for creating a new deadline."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "File Probate Petition",
                    "description": "File initial petition with the court",
                    "due_date": "2025-03-15",
                    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "reminder_config": {"days_before": [30, 7, 1]},
                }
            ]
        },
    )

    title: str
    description: str | None = None
    due_date: date
    task_id: UUID | None = None
    assigned_to: UUID | None = None
    reminder_config: dict | None = None


class DeadlineUpdate(BaseModel):
    """Schema for updating a deadline."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "File Probate Petition (Extended)",
                    "due_date": "2025-04-15",
                    "status": "extended",
                }
            ]
        },
    )

    title: str | None = None
    description: str | None = None
    due_date: date | None = None
    status: DeadlineStatus | None = None
    assigned_to: UUID | None = None
    reminder_config: dict | None = None


class DeadlineResponse(BaseModel):
    """Schema for deadline response."""

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "matter_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "task_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                    "title": "File Probate Petition",
                    "description": "File initial petition with the court",
                    "due_date": "2025-03-15",
                    "source": "manual",
                    "rule": None,
                    "status": "upcoming",
                    "assigned_to": None,
                    "reminder_config": {"days_before": [30, 7, 1]},
                    "last_reminder_sent": None,
                    "created_at": "2025-01-15T10:30:00Z",
                    "updated_at": "2025-01-15T10:30:00Z",
                }
            ]
        },
    )

    id: UUID
    matter_id: UUID
    task_id: UUID | None
    title: str
    description: str | None
    due_date: date
    source: DeadlineSource
    rule: dict | None
    status: DeadlineStatus
    assigned_to: UUID | None
    reminder_config: dict | None
    last_reminder_sent: datetime | None
    created_at: datetime
    updated_at: datetime


class DeadlineListResponse(BaseModel):
    """Paginated list of deadlines."""

    model_config = ConfigDict(strict=True)

    data: list[DeadlineResponse]
    meta: PaginationMeta
