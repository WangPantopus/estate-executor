from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Index, LargeBinary, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import EstateType, MatterPhase, MatterStatus

if TYPE_CHECKING:
    from app.models.assets import Asset
    from app.models.communications import Communication
    from app.models.deadlines import Deadline
    from app.models.documents import Document
    from app.models.entities import Entity
    from app.models.firms import Firm
    from app.models.stakeholders import Stakeholder
    from app.models.tasks import Task


class Matter(BaseModel):
    __table_args__ = (Index("ix_matters_firm_id_status", "firm_id", "status"),)

    firm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[MatterStatus] = mapped_column(
        Enum(MatterStatus, name="matter_status", native_enum=True),
        nullable=False,
        server_default="active",
    )
    estate_type: Mapped[EstateType] = mapped_column(
        Enum(EstateType, name="estate_type", native_enum=True),
        nullable=False,
    )
    jurisdiction_state: Mapped[str] = mapped_column(String(2), nullable=False)
    date_of_death: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_of_incapacity: Mapped[date | None] = mapped_column(Date, nullable=True)
    decedent_name: Mapped[str] = mapped_column(String, nullable=False)
    decedent_ssn_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    phase: Mapped[MatterPhase] = mapped_column(
        Enum(MatterPhase, name="matter_phase", native_enum=True),
        nullable=False,
        server_default="immediate",
    )
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    firm: Mapped[Firm] = relationship(back_populates="matters")
    stakeholders: Mapped[list[Stakeholder]] = relationship(
        back_populates="matter", cascade="all, delete-orphan"
    )
    tasks: Mapped[list[Task]] = relationship(back_populates="matter", cascade="all, delete-orphan")
    assets: Mapped[list[Asset]] = relationship(
        back_populates="matter", cascade="all, delete-orphan"
    )
    entities: Mapped[list[Entity]] = relationship(
        back_populates="matter", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="matter", cascade="all, delete-orphan"
    )
    deadlines: Mapped[list[Deadline]] = relationship(
        back_populates="matter", cascade="all, delete-orphan"
    )
    communications: Mapped[list[Communication]] = relationship(
        back_populates="matter", cascade="all, delete-orphan"
    )
