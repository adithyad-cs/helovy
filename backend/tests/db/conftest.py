"""Database test fixtures (docs/11 §2.4): ``ps5_test`` as the migrator and as the app role."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine

from app.core.config import Settings
from tests.services import (  # noqa: F401 - pytest discovers fixtures by name
    clean_tables,
    migrated_database,
    migrator_engine,
)
from tests.services import settings as settings


@pytest.fixture(scope="session")
def app_engine(settings: Settings) -> Iterator[Engine]:
    """Connections as ``ps5_app``, the restricted runtime role (docs/06 §11)."""
    engine = create_engine(settings.database_url.get_secret_value(), pool_size=2)
    yield engine
    engine.dispose()
