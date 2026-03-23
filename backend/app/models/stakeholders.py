from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import InviteStatus, StakeholderRole

if TYPE_CHECKING:
    from app.models.matters import Matter
    from app.models.users import User


class Stakeholder(BaseModel):
    __table_args__ = (
        UniqueConstraint("matter_id", "email", name="uq_stakeholder_matter_email"),
        Index("ix_stakeholders_matter_id_role", "matter_id", "role"),
    )

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    email: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[StakeholderRole] = mapped_column(
        Enum(StakeholderRole, name="stakeholder_role", native_enum=True),
        nullable=False,
    )
    relationship_label: Mapped[str | None] = mapped_column("relationship", String, nullable=True)
    permissions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    invite_status: Mapped[InviteStatus] = mapped_column(
        Enum(InviteStatus, name="invite_status", native_enum=True),
        nullable=False,
        server_default="pending",
    )
    invite_token: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    notification_preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    matter: Mapped[Matter] = relationship(back_populates="stakeholders")
    user: Mapped[User | None] = relationship(back_populates="stakeholder_records")
