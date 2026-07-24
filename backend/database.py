"""
ARIA Database - SQLAlchemy async engine and session management.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func
from datetime import datetime
from uuid import uuid4
import uuid as uuid_mod

from config import get_settings

settings = get_settings()

_is_sqlite = settings.database_url.startswith("sqlite")

_engine_kwargs = dict(
    echo=settings.debug,
)

if _is_sqlite:
    from sqlalchemy.pool import NullPool

    _engine_kwargs.update(
        connect_args={"check_same_thread": False, "timeout": 30},
        poolclass=NullPool,
    )
else:
    # PostgreSQL / other: use connection pooling
    _engine_kwargs.update(
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=10,
    )

engine = create_async_engine(settings.database_url, **_engine_kwargs)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin for UUID primary key."""
    id: Mapped[uuid_mod.UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )


async def get_db() -> AsyncSession:
    """Dependency for getting a database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        if _is_sqlite:
            from sqlalchemy import text
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Dispose engine on shutdown."""
    await engine.dispose()
