"""Pydantic schemas for enterprise SSO configuration."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SSOConfigCreate(BaseModel):
    """Create or update SSO configuration for a firm."""

    model_config = ConfigDict(strict=True)

    protocol: Literal["saml", "oidc"]

    # SAML
    saml_metadata_url: str | None = None
    saml_metadata_xml: str | None = None

    # OIDC
    oidc_discovery_url: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None

    # Settings
    enforce_sso: bool = False
    auto_provision: bool = True
    default_role: Literal["owner", "admin", "member"] = "member"
    allowed_domains: list[str] = []


class SSOConfigUpdate(BaseModel):
    """Partial update for SSO configuration."""

    model_config = ConfigDict(strict=True)

    protocol: Literal["saml", "oidc"] | None = None
    saml_metadata_url: str | None = None
    saml_metadata_xml: str | None = None
    oidc_discovery_url: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    enabled: bool | None = None
    enforce_sso: bool | None = None
    auto_provision: bool | None = None
    default_role: Literal["owner", "admin", "member"] | None = None
    allowed_domains: list[str] | None = None


class SSOConfigResponse(BaseModel):
    """SSO configuration response (secrets redacted)."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    firm_id: UUID
    protocol: str
    saml_metadata_url: str | None = None
    saml_entity_id: str | None = None
    saml_sso_url: str | None = None
    oidc_discovery_url: str | None = None
    oidc_client_id: str | None = None
    # oidc_client_secret intentionally excluded
    auth0_connection_id: str | None = None
    auth0_connection_name: str | None = None
    enabled: bool
    enforce_sso: bool
    auto_provision: bool
    default_role: str
    allowed_domains: list[str] = []
    verified: bool
    verified_at: datetime | None = None
    last_login_at: datetime | None = None
    configured_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class SSOLoginUrlResponse(BaseModel):
    """Response with the SSO login URL for a firm."""

    model_config = ConfigDict(strict=True)

    login_url: str
    connection_name: str
    protocol: str


class SSOTestResponse(BaseModel):
    """Response from SSO connection test."""

    model_config = ConfigDict(strict=True)

    success: bool
    message: str
    details: dict[str, Any] | None = None
