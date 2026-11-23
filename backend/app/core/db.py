"""Database engine (SQLAlchemy 2.0 + psycopg 3, synchronous; docs/04 §5).

The server connects with the restricted ``ps5_app`` role from ``DATABASE_URL``.
Sessions and transactions arrive with the first tables in M1.
"""

from __future__ import annotations

import logging

from sqlalchemy import Engine, create_engine, text

from app.core.config import Settings

CONNECT_TIMEOUT_S = 3

logger = logging.getLogger("app.db")


def create_db_engine(settings: Settings) -> Engine:
    """Create the pooled engine. No connection is opened until it is first used."""
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_S, "application_name": "hive-docs"},
    )


def database_is_ready(engine: Engine) -> bool:
    """Readiness check: ``SELECT 1`` with the app role (docs/07 E-02)."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any failure means "not ready"
        logger.warning("database readiness check failed: %s", type(exc).__name__)
        return False
    return True
