"""Beneficiary Portal schemas — read-only views for beneficiaries."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PortalMatterSummary(BaseModel):
    """Simplified matter view for beneficiaries."""

    model_config = ConfigDict(strict=True)

    matter_id: UUID
    decedent_name: str
    estate_type: str
    jurisdiction_state: str
    phase: str
    completion_percentage: float
    estimated_completion: str | None = None


class PortalContactInfo(BaseModel):
    """Lead professional contact info visible to beneficiaries."""

    model_config = ConfigDict(strict=True)

    name: str
    email: str
    role: str


class PortalMilestone(BaseModel):
    """A milestone event visible to beneficiaries."""

    model_config = ConfigDict(strict=True)

    title: str
    date: str
    completed: bool
    is_next: bool = False


class PortalDistributionSummary(BaseModel):
    """Distribution summary visible to beneficiary (if disclosed)."""

    model_config = ConfigDict(strict=True)

    total_estate_value: float | None = None
    distribution_status: str
    notices_count: int
    pending_acknowledgments: int


class PortalOverviewResponse(BaseModel):
    """Full overview response for the beneficiary portal."""

    model_config = ConfigDict(strict=True)

    matter: PortalMatterSummary
    your_role: str
    your_relationship: str | None = None
    contacts: list[PortalContactInfo]
    milestones: list[PortalMilestone]
    distribution: PortalDistributionSummary
    firm_name: str
    firm_logo_url: str | None = None


class PortalDocumentItem(BaseModel):
    """A document shared with the beneficiary."""

    model_config = ConfigDict(strict=True)

    id: UUID
    filename: str
    doc_type: str | None = None
    size_bytes: int
    shared_at: datetime


class PortalDocumentsResponse(BaseModel):
    """Documents shared with the beneficiary."""

    model_config = ConfigDict(strict=True)

    documents: list[PortalDocumentItem]
    total: int


class PortalMessageItem(BaseModel):
    """A communication visible to the beneficiary."""

    model_config = ConfigDict(strict=True)

    id: UUID
    sender_name: str
    type: str
    subject: str | None = None
    body: str
    created_at: datetime
    requires_acknowledgment: bool = False
    acknowledged: bool = False


class PortalMessagesResponse(BaseModel):
    """Messages visible to the beneficiary."""

    model_config = ConfigDict(strict=True)

    messages: list[PortalMessageItem]
    total: int


class PortalMessageCreate(BaseModel):
    """Schema for beneficiary posting a message."""

    model_config = ConfigDict(strict=True)

    subject: str | None = None
    body: str


class PortalMatterBrief(BaseModel):
    """Brief matter info for beneficiary matters list."""

    model_config = ConfigDict(strict=True)

    matter_id: UUID
    firm_id: UUID
    decedent_name: str
    phase: str
    firm_name: str


class PortalBeneficiaryMattersResponse(BaseModel):
    """List of matters where user is a beneficiary."""

    model_config = ConfigDict(strict=True)

    matters: list[PortalMatterBrief]
