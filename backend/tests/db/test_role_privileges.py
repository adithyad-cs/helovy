"""Schema and database privileges of the restricted app role (docs/06 §11; Render preparation).

Migration ``0005_app_role_privileges`` grants ``ps5_app`` USAGE on ``public`` and CONNECT on
the current database, so a managed server without the local init script (Render Postgres)
gets the same runtime privileges. These tests check the result at head, re-apply the
migration after the privileges were removed (the managed-server case), and check the guard
that refuses an over-privileged app role.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import Settings
from tests.services import alembic_config

INSUFFICIENT_PRIVILEGE = "42501"
UNDEFINED_OBJECT = "42704"
MIGRATION = (
    Path(__file__).resolve().parents[2] / "alembic" / "versions" / "0005_app_role_privileges.py"
)


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0005", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None)


def _scalar(engine: Engine, sql: str) -> object:
    with engine.connect() as connection:
        return connection.execute(text(sql)).scalar_one()


@pytest.fixture
def fresh_app_engine(settings: Settings) -> Iterator[Engine]:
    """A new app-role pool, so no connection opened before a privilege change is reused."""
    engine = create_engine(settings.database_url.get_secret_value(), poolclass=NullPool)
    yield engine
    engine.dispose()


def test_head_is_the_privileges_migration(migrator_engine: Engine) -> None:
    assert _scalar(migrator_engine, "SELECT version_num FROM alembic_version") == (
        "0005_app_role_privileges"
    )


def test_app_role_has_schema_usage_and_connect_but_cannot_create(
    migrator_engine: Engine,
) -> None:
    with migrator_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT has_schema_privilege('ps5_app', 'public', 'USAGE'), "
                "has_schema_privilege('ps5_app', 'public', 'CREATE'), "
                "has_database_privilege('ps5_app', current_database(), 'CONNECT'), "
                "has_database_privilege('ps5_app', current_database(), 'CREATE')"
            )
        ).one()
    assert tuple(row) == (True, False, True, False)


def test_public_cannot_create_in_the_public_schema(migrator_engine: Engine) -> None:
    acl = _scalar(
        migrator_engine,
        "SELECT coalesce(array_to_string(nspacl, ','), '') FROM pg_namespace "
        "WHERE nspname = 'public'",
    )
    entries = str(acl).split(",")
    assert not any(entry.startswith("=") and "C" in entry.split("/")[0] for entry in entries)


def test_app_role_attributes_are_restricted(migrator_engine: Engine) -> None:
    with migrator_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls, "
                "rolcanlogin, pg_has_role('ps5_app', current_user, 'MEMBER') "
                "FROM pg_roles WHERE rolname = 'ps5_app'"
            )
        ).one()
    assert tuple(row) == (False, False, False, False, False, True, False)


def test_migrator_is_not_the_app_role(migrator_engine: Engine, app_engine: Engine) -> None:
    assert _scalar(migrator_engine, "SELECT current_user") == "ps5_migrator"
    assert _scalar(app_engine, "SELECT current_user") == "ps5_app"


@pytest.mark.parametrize(
    "statement",
    [
        "SET ROLE ps5_migrator",
        "CREATE SCHEMA app_role_probe",
        "CREATE TABLE public.app_role_probe (id int)",
        "CREATE FUNCTION public.app_role_probe() RETURNS int LANGUAGE sql AS 'SELECT 1'",
        "ALTER TABLE documents ADD COLUMN probe int",
    ],
)
def test_app_role_cannot_escalate_or_run_ddl(app_engine: Engine, statement: str) -> None:
    with pytest.raises(DBAPIError) as raised, app_engine.begin() as connection:
        connection.execute(text(statement))
    assert _sqlstate(raised.value) == INSUFFICIENT_PRIVILEGE


def test_app_role_cannot_pass_its_privileges_on(
    app_engine: Engine, migrator_engine: Engine
) -> None:
    # Without GRANT OPTION, PostgreSQL only warns "no privileges were granted".
    with app_engine.begin() as connection:
        connection.execute(text("GRANT SELECT, INSERT ON documents TO PUBLIC"))
    granted = _scalar(
        migrator_engine,
        "SELECT count(*) FROM information_schema.role_table_grants "
        "WHERE grantee = 'PUBLIC' AND table_schema = 'public'",
    )
    assert granted == 0


def test_migration_restores_privileges_missing_on_a_managed_server(
    migrator_engine: Engine, fresh_app_engine: Engine
) -> None:
    """Render case: no init script gave ps5_app USAGE or CONNECT; the migration grants them."""
    revoke = (
        "REVOKE USAGE ON SCHEMA public FROM ps5_app",
        "DO $$ BEGIN EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM ps5_app', "
        "current_database()); END $$",
    )
    regrant = (
        "GRANT USAGE ON SCHEMA public TO ps5_app",
        "DO $$ BEGIN EXECUTE format('GRANT CONNECT ON DATABASE %I TO ps5_app', "
        "current_database()); END $$",
    )
    try:
        with migrator_engine.begin() as connection:
            for statement in revoke:
                connection.execute(text(statement))
            assert (
                connection.execute(
                    text("SELECT has_schema_privilege('ps5_app', 'public', 'USAGE')")
                ).scalar_one()
                is False
            )
        with pytest.raises(DBAPIError) as refused, fresh_app_engine.connect() as connection:
            connection.execute(text("SELECT count(*) FROM documents"))
        assert "permission denied" in str(refused.value)  # CONNECT (or USAGE) denied

        command.downgrade(alembic_config(), "0004_issuance")  # 0005 downgrade: no change
        command.upgrade(alembic_config(), "head")

        with fresh_app_engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM documents")).scalar_one() == 0
    finally:
        command.upgrade(alembic_config(), "head")  # never leave the shared database behind
        with migrator_engine.begin() as connection:
            for statement in regrant:
                connection.execute(text(statement))
    assert _scalar(migrator_engine, "SELECT version_num FROM alembic_version") == (
        "0005_app_role_privileges"
    )


def test_guard_accepts_the_restricted_app_role(migrator_engine: Engine) -> None:
    with migrator_engine.begin() as connection:
        connection.execute(text(_migration().restricted_role_guard("ps5_app")))


def test_guard_refuses_a_superuser_as_app_role(migrator_engine: Engine) -> None:
    # The postgres image's bootstrap superuser stands in for a wrongly created app role.
    with pytest.raises(DBAPIError) as raised, migrator_engine.begin() as connection:
        connection.execute(text(_migration().restricted_role_guard("postgres")))
    assert _sqlstate(raised.value) == INSUFFICIENT_PRIVILEGE
    assert "restricted login role" in str(raised.value)


def test_guard_refuses_a_missing_app_role(migrator_engine: Engine) -> None:
    with pytest.raises(DBAPIError) as raised, migrator_engine.begin() as connection:
        connection.execute(text(_migration().restricted_role_guard("ps5_app_missing")))
    assert _sqlstate(raised.value) == UNDEFINED_OBJECT
    assert "create it before migrating" in str(raised.value)


def test_guard_refuses_an_app_role_that_inherits_the_migrator(migrator_engine: Engine) -> None:
    # The migrating role is trivially a member of itself: the guard must refuse it.
    with pytest.raises(DBAPIError) as raised, migrator_engine.begin() as connection:
        connection.execute(text(_migration().restricted_role_guard("ps5_migrator")))
    assert _sqlstate(raised.value) == INSUFFICIENT_PRIVILEGE
    assert "must not be a member" in str(raised.value)
