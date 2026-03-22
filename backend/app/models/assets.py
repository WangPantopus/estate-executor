from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, LargeBinary, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import AssetStatus, AssetType, OwnershipType, TransferMechanism

if TYPE_CHECKING:
    from app.models.documents import Document
    from app.models.entities import Entity
    from app.models.matters import Matter


class Asset(BaseModel):
    __table_args__ = (Index("ix_assets_matter_id_asset_type", "matter_id", "asset_type"),)

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type", native_enum=True),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    institution: Mapped[str | None] = mapped_column(String, nullable=True)
    account_number_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    ownership_type: Mapped[OwnershipType] = mapped_column(
        Enum(OwnershipType, name="ownership_type", native_enum=True),
        nullable=False,
    )
    transfer_mechanism: Mapped[TransferMechanism] = mapped_column(
        Enum(TransferMechanism, name="transfer_mechanism", native_enum=True),
        nullable=False,
    )
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus, name="asset_status", native_enum=True),
        nullable=False,
        server_default="discovered",
    )
    date_of_death_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    current_estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    final_appraised_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")

    matter: Mapped[Matter] = relationship(back_populates="assets")
    entities: Mapped[list[Entity]] = relationship(
        secondary="entity_assets", back_populates="assets"
    )
    documents: Mapped[list[Document]] = relationship(
        secondary="asset_documents", back_populates="assets"
    )
