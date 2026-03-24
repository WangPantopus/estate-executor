"""Distribution model — tracks distributions of assets/cash to beneficiaries."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import DistributionType

if TYPE_CHECKING:
    from app.models.assets import Asset
    from app.models.matters import Matter
    from app.models.stakeholders import Stakeholder


class Distribution(BaseModel):
    __table_args__ = (
        Index("ix_distributions_matter_id", "matter_id"),
        Index("ix_distributions_beneficiary", "beneficiary_stakeholder_id"),
    )

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    beneficiary_stakeholder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stakeholders.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    distribution_type: Mapped[DistributionType] = mapped_column(
        Enum(DistributionType, name="distribution_type", native_enum=True),
        nullable=False,
    )
    distribution_date: Mapped[date] = mapped_column(Date, nullable=False)
    receipt_acknowledged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    receipt_acknowledged_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    matter: Mapped[Matter] = relationship(back_populates="distributions")
    asset: Mapped[Asset | None] = relationship()
    beneficiary: Mapped[Stakeholder] = relationship(foreign_keys=[beneficiary_stakeholder_id])
