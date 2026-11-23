"""Database engine, ORM base and request sessions (SQLAlchemy 2.0 + psycopg 3; docs/04 §5).

The server connects with the restricted ``ps5_app`` role from ``DATABASE_URL``. There is
one ORM session per request; service functions open explicit ``with db.begin():`` blocks.
Isolation is READ COMMITTED (the PostgreSQL default). The schema itself is created only by
the hand-written Alembic migrations (docs/06 §14); the models below map those tables.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings

CONNECT_TIMEOUT_S = 3

logger = logging.getLogger("app.db")


class Base(DeclarativeBase):
    """Declarative base for every module's models. Never used to create tables."""


def create_db_engine(settings: Settings) -> Engine:
    """Create the pooled engine. No connection is opened until it is first used."""
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_S, "application_name": "hive-docs"},
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False, autoflush=False)


def get_db(request: Request) -> Iterator[Session]:
    """FastAPI dependency: one session per request, closed when the request ends."""
    factory: sessionmaker[Session] = request.app.state.db_sessions
    with factory() as session:
        yield session


def database_is_ready(engine: Engine) -> bool:
    """Readiness check: ``SELECT 1`` with the app role (docs/07 E-02)."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any failure means "not ready"
        logger.warning("database readiness check failed: %s", type(exc).__name__)
        return False
    return True
