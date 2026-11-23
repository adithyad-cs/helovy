"""Alembic environment: migrations run as the owner role from MIGRATION_DATABASE_URL.

The running server never runs DDL (docs/06 §14, rule 3). Migrations are written by hand as
explicit SQL, so there is no autogenerate metadata here. A caller (the test suite) may pass
the URL explicitly through ``config.attributes["database_url"]``.
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.core.config import load_migration_url

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def _database_url() -> str:
    explicit = config.attributes.get("database_url")
    return str(explicit) if explicit else load_migration_url()


def run_migrations_offline() -> None:
    context.configure(url=_database_url(), literal_binds=True, transaction_per_migration=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
