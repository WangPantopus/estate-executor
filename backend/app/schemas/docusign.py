"""Pydantic schemas for DocuSign e-signature endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

# ─── Send for signature ──────────────────────────────────────────────────────


class SignerInfo(BaseModel):
    model_config = ConfigDict(strict=True)

    email: EmailStr
    name: str
    role: str = "signer"  # signer | cc
    stakeholder_id: UUID | None = None


class SendForSignatureRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    document_id: UUID
    request_type: Literal[
        "distribution_consent",
        "beneficiary_acknowledgment",
        "executor_oath",
        "general",
    ] = "general"
    subject: str
    message: str | None = None
    signers: list[SignerInfo]


# ─── Response schemas ────────────────────────────────────────────────────────


class SignerResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    email: str
    name: str
    role: str
    status: str | None = None
    signed_at: str | None = None
    stakeholder_id: str | None = None


class SignatureRequestResponse(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    matter_id: UUID
    document_id: UUID | None = None
    request_type: str
    status: str
    envelope_id: str | None = None
    subject: str
    message: str | None = None
    signers: list[dict] = []
    sent_by: UUID
    sent_at: datetime | None = None
    completed_at: datetime | None = None
    voided_at: datetime | None = None
    expires_at: datetime | None = None
    signed_document_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class SignatureRequestListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    data: list[SignatureRequestResponse]
    total: int


# ─── Void request ────────────────────────────────────────────────────────────


class VoidEnvelopeRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    reason: str = "Voided by estate administrator"
