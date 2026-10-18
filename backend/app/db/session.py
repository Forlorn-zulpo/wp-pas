from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


# Note: models must not be imported here (it would create a circular import,
# since every model imports Base from this module). Anything that needs the
# full mapped schema — app.main, migrations/env.py, tests/conftest.py —
# imports `app.models` itself to register every model before first use.


# Sync engine: used by Alembic migrations and Celery workers.
sync_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False, future=True)

# Async engine: used by FastAPI request handlers.
async_engine = create_async_engine(settings.ASYNC_DATABASE_URL, pool_pre_ping=True, future=True)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()
