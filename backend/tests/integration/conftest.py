import os
import subprocess
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_REPO_ROOT = Path(__file__).resolve().parents[3]  # /app inside the container


@pytest.fixture(scope="session", autouse=True)
def _migrate_db() -> None:
    # Build the real schema once, from the actual migrations (source of truth):
    # tables, enums, the audit immutability trigger — everything.
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=_REPO_ROOT,
        env=os.environ.copy(),
        check=True,
    )


def _async_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+asyncpg://", 1)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(_async_url())
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()
