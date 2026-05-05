"""
Database session management using SQLAlchemy async engine.

Provides:
  - Async engine + session factory
  - Dependency injection for FastAPI routes
  - Database initialization (create tables)
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields a database session per request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables. Called on app startup.

    When USE_ALEMBIC=true, this is skipped in favor of `alembic upgrade head`.
    """
    import os
    if os.environ.get("USE_ALEMBIC", "").lower() == "true":
        return
    from app.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close engine. Called on app shutdown."""
    await engine.dispose()
