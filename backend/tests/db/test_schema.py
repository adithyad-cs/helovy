"""DB-01: ``alembic upgrade head`` on an empty ps5_test creates every documented name."""

from __future__ import annotations

from sqlalchemy import Engine, text

from tests.db import expected_schema as expected
from tests.services import reset_schema, upgrade_to_head


def _names(engine: Engine, sql: str) -> set[str]:
    with engine.connect() as connection:
        return set(connection.execute(text(sql)).scalars())


def test_db_01_upgrade_from_empty_creates_every_documented_name(migrator_engine: Engine) -> None:
    reset_schema(migrator_engine)
    assert (
        _names(migrator_engine, "SELECT tablename FROM pg_tables WHERE schemaname='public'")
        == set()
    )
    upgrade_to_head()

    tables = _names(migrator_engine, "SELECT tablename FROM pg_tables WHERE schemaname='public'")
    assert expected.TABLES | {"alembic_version"} == tables
    constraints = _names(
        migrator_engine,
        "SELECT conname FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace "
        "WHERE n.nspname = 'public'",
    )
    assert expected.CONSTRAINTS <= constraints, expected.CONSTRAINTS - constraints
    indexes = _names(migrator_engine, "SELECT indexname FROM pg_indexes WHERE schemaname='public'")
    assert expected.INDEXES <= indexes, expected.INDEXES - indexes
    triggers = _names(migrator_engine, "SELECT tgname FROM pg_trigger WHERE NOT tgisinternal")
    assert expected.TRIGGERS == triggers


def test_every_table_is_owned_by_the_migrator(migrator_engine: Engine) -> None:
    owners = _names(
        migrator_engine, "SELECT DISTINCT tableowner FROM pg_tables WHERE schemaname='public'"
    )
    assert owners == {"ps5_migrator"}


def test_no_money_column_uses_floating_point(migrator_engine: Engine) -> None:
    # docs/06 §1, §5: numeric only; never real, double precision or money.
    floats = _names(
        migrator_engine,
        "SELECT table_name || '.' || column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND data_type IN ('real', 'double precision', 'money')",
    )
    assert floats == set()
