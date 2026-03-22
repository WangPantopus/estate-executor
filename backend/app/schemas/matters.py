"""Matter schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EstateType, MatterPhase, MatterStatus

from .common import PaginationMeta


class MatterCreate(BaseModel):
    """Schema for creating a new matter."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "Estate of John Doe",
                    "estate_type": "testate_probate",
                    "jurisdiction_state": "CA",
                    "decedent_name": "John Doe",
                    "date_of_death": "2025-01-01",
                    "estimated_value": "1500000.00",
                }
            ]
        },
    )

    title: str
    estate_type: EstateType
    jurisdiction_state: str = Field(..., min_length=2, max_length=2)
    decedent_name: str
    date_of_death: date | None = None
    date_of_incapacity: date | None = None
    estimated_value: Decimal | None = Field(None, max_digits=15, decimal_places=2)
    asset_types_present: list[str] | None = None
    flags: list[str] | None = None


class MatterUpdate(BaseModel):
    """Schema for updating a matter."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "Estate of John Doe (Updated)",
                    "status": "active",
                    "phase": "administration",
                }
            ]
        },
    )

    title: str | None = None
    status: MatterStatus | None = None
    phase: MatterPhase | None = None
    jurisdiction_state: str | None = Field(None, min_length=2, max_length=2)
    estimated_value: Decimal | None = Field(None, max_digits=15, decimal_places=2)
    settings: dict | None = None


class MatterResponse(BaseModel):
    """Schema for matter response."""

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "firm_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "title": "Estate of John Doe",
                    "status": "active",
                    "estate_type": "testate_probate",
                    "jurisdiction_state": "CA",
                    "date_of_death": "2025-01-01",
                    "decedent_name": "John Doe",
                    "estimated_value": "1500000.00",
                    "phase": "immediate",
                    "created_at": "2025-01-15T10:30:00Z",
                    "updated_at": "2025-01-15T10:30:00Z",
                    "closed_at": None,
                }
            ]
        },
    )

    id: UUID
    firm_id: UUID
    title: str
    status: MatterStatus
    estate_type: EstateType
    jurisdiction_state: str
    date_of_death: date | None
    decedent_name: str
    estimated_value: Decimal | None
    phase: MatterPhase
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None


class TaskSummary(BaseModel):
    """Summary of task counts and progress for a matter."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "total": 50,
                    "not_started": 20,
                    "in_progress": 10,
                    "blocked": 2,
                    "complete": 15,
                    "waived": 3,
                    "overdue": 1,
                    "completion_percentage": 30.0,
                }
            ]
        },
    )

    total: int
    not_started: int
    in_progress: int
    blocked: int
    complete: int
    waived: int
    overdue: int
    completion_percentage: float


class AssetSummary(BaseModel):
    """Summary of assets for a matter."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "total_count": 12,
                    "total_estimated_value": "2500000.00",
                    "by_type": {"real_estate": 2, "bank_account": 5},
                    "by_status": {"discovered": 8, "valued": 4},
                }
            ]
        },
    )

    total_count: int
    total_estimated_value: Decimal | None
    by_type: dict[str, int]
    by_status: dict[str, int]


class MatterListResponse(BaseModel):
    """Paginated list of matters."""

    model_config = ConfigDict(strict=True)

    data: list[MatterResponse]
    meta: PaginationMeta


# Forward references for MatterDashboard - these are imported at runtime
# to avoid circular imports. DeadlineResponse and EventResponse are defined
# in their respective schema modules.


class MatterDashboard(BaseModel):
    """Dashboard view for a single matter."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "matter": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "firm_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                        "title": "Estate of John Doe",
                        "status": "active",
                        "estate_type": "testate_probate",
                        "jurisdiction_state": "CA",
                        "date_of_death": "2025-01-01",
                        "decedent_name": "John Doe",
                        "estimated_value": "1500000.00",
                        "phase": "immediate",
                        "created_at": "2025-01-15T10:30:00Z",
                        "updated_at": "2025-01-15T10:30:00Z",
                        "closed_at": None,
                    },
                    "task_summary": {
                        "total": 50,
                        "not_started": 20,
                        "in_progress": 10,
                        "blocked": 2,
                        "complete": 15,
                        "waived": 3,
                        "overdue": 1,
                        "completion_percentage": 30.0,
                    },
                    "asset_summary": {
                        "total_count": 12,
                        "total_estimated_value": "2500000.00",
                        "by_type": {"real_estate": 2},
                        "by_status": {"discovered": 8},
                    },
                    "stakeholder_count": 5,
                    "upcoming_deadlines": [],
                    "recent_events": [],
                }
            ]
        },
    )

    matter: MatterResponse
    task_summary: TaskSummary
    asset_summary: AssetSummary
    stakeholder_count: int
    upcoming_deadlines: list[DeadlineResponse]
    recent_events: list[EventResponse]


# Deferred imports to avoid circular dependencies
from .deadlines import DeadlineResponse  # noqa: E402
from .events import EventResponse  # noqa: E402

MatterDashboard.model_rebuild()
