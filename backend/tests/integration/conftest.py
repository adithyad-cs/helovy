"""Integration fixtures: real PostgreSQL (``ps5_test``) and real SeaweedFS (test bucket).

The fixtures live in tests/services.py, shared with the database tests (tests/db).
"""

from __future__ import annotations

from tests.services import (  # noqa: F401 - pytest discovers fixtures by name
    SPA_INDEX,
    build_test_spa,
    clean_tables,
    client,
    clock,
    make_client,
    migrated_database,
    migrator_engine,
    no_spa,
    s3,
    settings,
    test_bucket,
)
