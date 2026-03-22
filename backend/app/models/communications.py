from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import CommunicationType, CommunicationVisibility

if TYPE_CHECKING:
    from app.models.matters import Matter
    from app.models.stakeholders import Stakeholder


class Communication(BaseModel):
    __table_args__ = (Index("ix_communications_matter_id_type", "matter_id", "type"),)

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stakeholders.id", ondelete="SET NULL"),
        nullable=False,
    )
    type: Mapped[CommunicationType] = mapped_column(
        Enum(CommunicationType, name="communication_type", native_enum=True),
        nullable=False,
    )
    subject: Mapped[str | None] = mapped_column(String, nullable=True)
    body: Mapped[str] = mapped_column(String, nullable=False)
    visibility: Mapped[CommunicationVisibility] = mapped_column(
        Enum(
            CommunicationVisibility,
            name="communication_visibility",
            native_enum=True,
        ),
        nullable=False,
    )
    visible_to: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    acknowledged_by: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )

    matter: Mapped[Matter] = relationship(back_populates="communications")
    sender: Mapped[Stakeholder] = relationship(foreign_keys=[sender_id])
