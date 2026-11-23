"""DB-08 (M1 part): the app role's privileges on the identity tables (docs/06 §11).

The full DB-08 (document_snapshots, stored_files, templates) is completed with 0003/0004.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from tests.db import expected_schema as expected

INSUFFICIENT_PRIVILEGE = "42501"


def _sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None)


def _denied(engine: Engine, statement: str) -> None:
    with pytest.raises(DBAPIError) as raised, engine.begin() as connection:
        connection.execute(text(statement))
    assert _sqlstate(raised.value) == INSUFFICIENT_PRIVILEGE


def test_app_role_inserts_audit_events_without_a_sequence_grant(app_engine: Engine) -> None:
    # docs/06 §11 asks to verify whether the identity sequence needs USAGE: it does not.
    with app_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO audit_events (event_type) VALUES ('auth.login_failed')")
        )
        assert connection.execute(text("SELECT count(*) FROM audit_events")).scalar_one() == 1


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_events SET details = '{}'::jsonb",
        "DELETE FROM audit_events",
        "DELETE FROM sessions",
        "DELETE FROM users",
        "DELETE FROM organizations",
        "DELETE FROM memberships",
        "DELETE FROM businesses",
        "DELETE FROM customers",
    ],
)
def test_app_role_cannot_update_or_delete_where_not_granted(
    app_engine: Engine, statement: str
) -> None:
    _denied(app_engine, statement)


@pytest.mark.parametrize("table", sorted(expected.TABLES))
def test_app_role_is_never_granted_truncate(app_engine: Engine, table: str) -> None:
    _denied(app_engine, f"TRUNCATE {table}")


def test_app_role_has_no_ddl(app_engine: Engine) -> None:
    _denied(app_engine, "CREATE TABLE app_role_probe (id int)")


def test_app_role_privileges_match_docs_06_section_11(migrator_engine: Engine) -> None:
    with migrator_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT table_name, string_agg(privilege_type, ',' ORDER BY privilege_type) "
                "FROM information_schema.role_table_grants WHERE grantee = 'ps5_app' "
                "GROUP BY table_name"
            )
        ).all()
    grants = {table: set(privileges.split(",")) for table, privileges in rows}
    assert grants == {
        "organizations": {"SELECT", "INSERT", "UPDATE"},
        "users": {"SELECT", "INSERT", "UPDATE"},
        "memberships": {"SELECT", "INSERT", "UPDATE"},
        "sessions": {"SELECT", "INSERT", "UPDATE"},
        "audit_events": {"SELECT", "INSERT"},
        "businesses": {"SELECT", "INSERT", "UPDATE"},
        "customers": {"SELECT", "INSERT", "UPDATE"},
    }
