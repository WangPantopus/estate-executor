import re
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.core.database import Base


class BaseModel(Base):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(self) -> str:
        # Convert CamelCase to snake_case and pluralize
        name = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", self.__name__)
        name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        return name.lower() + "s"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=text("now()"),
    )
