import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

import backend.accounts.models  # noqa: F401

# All models must be imported here so their tables register on Base.metadata.
import backend.auth.models  # noqa: F401
import backend.cashflow.models  # noqa: F401
import backend.common.audit  # noqa: F401
import backend.crra.models  # noqa: F401
import backend.ingestion.models  # noqa: F401
import backend.market.models  # noqa: F401
import backend.telegram.models  # noqa: F401
from backend.common.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _db_url() -> str:
    url = os.environ["DATABASE_URL"]
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _db_url()
    engine = async_engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with engine.connect() as conn:
        await conn.run_sync(_do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
