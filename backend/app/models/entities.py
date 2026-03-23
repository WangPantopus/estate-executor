from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import EntityType, FundingStatus

if TYPE_CHECKING:
    from app.models.assets import Asset
    from app.models.matters import Matter


class Entity(BaseModel):
    __tablename__ = "entities"

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="entity_type", native_enum=True),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    trustee: Mapped[str | None] = mapped_column(String, nullable=True)
    successor_trustee: Mapped[str | None] = mapped_column(String, nullable=True)
    trigger_conditions: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    funding_status: Mapped[FundingStatus] = mapped_column(
        Enum(FundingStatus, name="funding_status", native_enum=True),
        nullable=False,
        server_default="unknown",
    )
    distribution_rules: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")

    matter: Mapped[Matter] = relationship(back_populates="entities")
    assets: Mapped[list[Asset]] = relationship(secondary="entity_assets", back_populates="entities")
