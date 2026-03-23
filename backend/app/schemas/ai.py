"""AI feature schemas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from uuid import UUID


class AIClassifyResponse(BaseModel):
    """Response from AI document classification."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "doc_type": "death_certificate",
                    "confidence": 0.95,
                    "reasoning": "Document contains official seal and death record fields.",
                }
            ]
        },
    )

    doc_type: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str


class AIExtractResponse(BaseModel):
    """Response from AI document data extraction."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "extracted_fields": {
                        "date_of_death": "2025-01-01",
                        "decedent_name": "John Doe",
                    },
                    "confidence": 0.92,
                }
            ]
        },
    )

    extracted_fields: dict
    confidence: float = Field(..., ge=0.0, le=1.0)


class AILetterDraftRequest(BaseModel):
    """Request to draft a letter for an asset."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "asset_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "letter_type": "claim_letter",
                }
            ]
        },
    )

    asset_id: UUID
    letter_type: str


class AILetterDraftResponse(BaseModel):
    """Response with a drafted letter."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "subject": "Notice of Death and Claim",
                    "body": "Dear Sir/Madam, ...",
                    "recipient_institution": "First National Bank",
                }
            ]
        },
    )

    subject: str
    body: str
    recipient_institution: str


class TaskSuggestion(BaseModel):
    """A single AI-suggested task."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "Notify IRS of Death",
                    "description": "File Form 56 to notify the IRS.",
                    "phase": "notification",
                    "reasoning": "Required for estates with tax obligations.",
                }
            ]
        },
    )

    title: str
    description: str
    phase: str
    reasoning: str


class AISuggestTasksResponse(BaseModel):
    """Response with AI-suggested tasks."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "suggestions": [
                        {
                            "title": "Notify IRS of Death",
                            "description": "File Form 56.",
                            "phase": "notification",
                            "reasoning": "Required for tax obligations.",
                        }
                    ]
                }
            ]
        },
    )

    suggestions: list[TaskSuggestion]


class Anomaly(BaseModel):
    """A detected anomaly in matter data."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "type": "valuation_discrepancy",
                    "description": "Asset value differs significantly from comparable.",
                    "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "asset_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "severity": "high",
                }
            ]
        },
    )

    type: str
    description: str
    document_id: UUID | None = None
    asset_id: UUID | None = None
    severity: str


class AIAnomalyResponse(BaseModel):
    """Response with detected anomalies."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "anomalies": [
                        {
                            "type": "valuation_discrepancy",
                            "description": "Asset value differs significantly.",
                            "severity": "high",
                        }
                    ]
                }
            ]
        },
    )

    anomalies: list[Anomaly]
