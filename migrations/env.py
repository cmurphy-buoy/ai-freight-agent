"""
Alembic environment configuration.

This file tells Alembic how to connect to your database and which models
to look at when generating migrations.

You don't need to edit this often — it's mostly boilerplate.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import your models so Alembic knows about your tables
from app.models import Base
from app.config import settings

# Alembic Config object — gives access to alembic.ini values
config = context.config

# Set the database URL from our app config (overrides alembic.ini)
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set up logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is what Alembic compares against to detect changes
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live database connection (generates SQL only)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Helper to run migrations with a connection."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations with an async database connection."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations with a live database connection."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
