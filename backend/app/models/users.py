from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.firm_memberships import FirmMembership
    from app.models.stakeholders import Stakeholder


class User(BaseModel):
    auth_provider_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)

    firm_memberships: Mapped[list[FirmMembership]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    stakeholder_records: Mapped[list[Stakeholder]] = relationship(back_populates="user")
