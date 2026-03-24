"""SSOConfig model — enterprise SSO configuration per firm."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.firms import Firm


class SSOConfig(BaseModel):
    """Stores SAML/OIDC SSO configuration for enterprise firms."""

    firm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # SSO protocol
    protocol: Mapped[str] = mapped_column(
        String, nullable=False, server_default="saml"
    )  # "saml" or "oidc"

    # SAML fields
    saml_metadata_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    saml_metadata_xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    saml_entity_id: Mapped[str | None] = mapped_column(String, nullable=True)
    saml_sso_url: Mapped[str | None] = mapped_column(String, nullable=True)
    saml_certificate: Mapped[str | None] = mapped_column(Text, nullable=True)

    # OIDC fields
    oidc_discovery_url: Mapped[str | None] = mapped_column(String, nullable=True)
    oidc_client_id: Mapped[str | None] = mapped_column(String, nullable=True)
    oidc_client_secret: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Auth0 enterprise connection ID (created via Management API)
    auth0_connection_id: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    auth0_connection_name: Mapped[str | None] = mapped_column(
        String, nullable=True
    )

    # Configuration
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    enforce_sso: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )  # If true, users MUST use SSO — no password login
    auto_provision: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )  # Auto-add SSO users to firm
    default_role: Mapped[str] = mapped_column(
        String, nullable=False, server_default="member"
    )  # Role assigned to auto-provisioned users

    # Allowed email domains (for domain-based auto-provisioning)
    allowed_domains: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )

    # Status
    verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Metadata
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )

    configured_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    firm: Mapped[Firm] = relationship()
