from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import QueuePool

from app.core.config import settings

# Production-tuned connection pool settings:
# - pool_size: base number of persistent connections
# - max_overflow: additional connections under burst load
# - pool_pre_ping: detect stale connections before use
# - pool_recycle: recycle connections every 30 minutes to avoid stale TCP
_pool_size = 10 if settings.is_production else 5
_max_overflow = 20 if settings.is_production else 15

engine = create_async_engine(
    settings.database_url,
    echo=settings.is_development,
    poolclass=QueuePool,
    pool_size=_pool_size,
    max_overflow=_max_overflow,
    pool_pre_ping=True,
    pool_recycle=1800,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass
