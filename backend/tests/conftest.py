import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

# Point at a dedicated test database BEFORE importing app modules that read settings.
TEST_ASYNC_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/app_test_db"
os.environ["ASYNC_DATABASE_URL"] = TEST_ASYNC_DB_URL
os.environ["DATABASE_URL"] = "postgresql+psycopg2://postgres:postgres@localhost:5432/app_test_db"

import app.models  # noqa: E402,F401  (registers every mapped model before Base.metadata is used)
from app.db.session import Base  # noqa: E402
from app.main import app  # noqa: E402


def _run_isolated(coro_factory):
    """Run a coroutine in its own event loop using a throwaway engine, so it
    never shares asyncpg connections with the app's own engine (which is
    bound to whatever loop TestClient happens to be using)."""

    async def _wrapper():
        engine = create_async_engine(TEST_ASYNC_DB_URL, poolclass=NullPool)
        try:
            await coro_factory(engine)
        finally:
            await engine.dispose()

    asyncio.run(_wrapper())


@pytest.fixture(scope="session", autouse=True)
def _prepare_database():
    async def _create(engine):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    _run_isolated(_create)
    yield

    async def _drop(engine):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    _run_isolated(_drop)


@pytest.fixture(autouse=True)
def _clean_tables():
    """Each test starts with empty tables so tests are independent and order-proof."""
    yield

    async def _clean(engine):
        async with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(table.delete())

    _run_isolated(_clean)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    # Drop the app's own engine connections so the next test's TestClient
    # (running in a fresh loop) doesn't inherit stale asyncpg connections.
    from app.db.session import async_engine

    asyncio.run(async_engine.dispose())
