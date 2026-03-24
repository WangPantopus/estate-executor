"""Time tracking schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from .common import PaginationMeta


class TimeEntryCreate(BaseModel):
    """Input for creating a time entry."""

    model_config = ConfigDict(strict=True)

    task_id: UUID | None = None
    hours: int = 0
    minutes: int = 0
    description: str
    entry_date: date
    billable: bool = True

    @field_validator("hours")
    @classmethod
    def hours_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Hours must be non-negative")
        return v

    @field_validator("minutes")
    @classmethod
    def minutes_valid(cls, v: int) -> int:
        if v < 0 or v > 59:
            raise ValueError("Minutes must be 0–59")
        return v


class TimeEntryUpdate(BaseModel):
    """Input for updating a time entry."""

    model_config = ConfigDict(strict=True)

    task_id: UUID | None = None
    hours: int | None = None
    minutes: int | None = None
    description: str | None = None
    entry_date: date | None = None
    billable: bool | None = None


class TimeEntryResponse(BaseModel):
    """Time entry response."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    matter_id: UUID
    task_id: UUID | None
    task_title: str | None = None
    stakeholder_id: UUID
    stakeholder_name: str = ""
    hours: int
    minutes: int
    description: str
    entry_date: date
    billable: bool
    created_at: datetime


class TimeEntryListResponse(BaseModel):
    """Paginated list of time entries."""

    model_config = ConfigDict(strict=True)

    data: list[TimeEntryResponse]
    meta: PaginationMeta


class TimeTrackingSummary(BaseModel):
    """Summary of time tracked for a matter."""

    model_config = ConfigDict(strict=True)

    total_hours: int
    total_minutes: int
    total_decimal_hours: float
    billable_hours: float
    non_billable_hours: float
    by_stakeholder: list[dict]
    by_task: list[dict]
