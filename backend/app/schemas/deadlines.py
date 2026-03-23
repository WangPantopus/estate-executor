"""Deadline schemas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from datetime import date, datetime
    from uuid import UUID

    from app.models.enums import DeadlineSource, DeadlineStatus

    from .common import PaginationMeta


class TaskBrief(BaseModel):
    """Brief task reference included in deadline responses."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    title: str
    status: str


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
    """Schema for deadline response with optional task brief and assignee name."""

    model_config = ConfigDict(strict=True, from_attributes=True)

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
    assignee_name: str | None = None
    task: TaskBrief | None = None
    reminder_config: dict | None
    last_reminder_sent: datetime | None
    created_at: datetime
    updated_at: datetime


class DeadlineListResponse(BaseModel):
    """Paginated list of deadlines."""

    model_config = ConfigDict(strict=True)

    data: list[DeadlineResponse]
    meta: PaginationMeta


class CalendarDeadline(BaseModel):
    """A single deadline entry in the calendar view."""

    model_config = ConfigDict(strict=True)

    id: UUID
    title: str
    description: str | None
    due_date: date
    status: str
    source: str
    task_id: UUID | None
    task_title: str | None
    assigned_to: UUID | None
    assignee_name: str | None


class CalendarMonth(BaseModel):
    """Deadlines grouped by month."""

    model_config = ConfigDict(strict=True)

    month: str
    deadlines: list[CalendarDeadline]


class CalendarResponse(BaseModel):
    """Calendar view of deadlines grouped by month."""

    model_config = ConfigDict(strict=True)

    data: list[CalendarMonth]
