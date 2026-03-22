from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import FirmRole

if TYPE_CHECKING:
    from app.models.firms import Firm
    from app.models.users import User


class FirmMembership(BaseModel):
    __table_args__ = (UniqueConstraint("firm_id", "user_id", name="uq_firm_membership_firm_user"),)

    firm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    firm_role: Mapped[FirmRole] = mapped_column(
        Enum(FirmRole, name="firm_role", native_enum=True),
        nullable=False,
    )

    firm: Mapped[Firm] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="firm_memberships")
