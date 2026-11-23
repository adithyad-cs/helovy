"""DB-07 (and, from later migrations, DB-03 to DB-06): triggers raise SQLSTATE 23001.

The triggers are tested as the migrator, which has the table privileges; as the app role the
statements are already refused by the grants (tests/db/test_grants.py).
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

RESTRICT_VIOLATION = "23001"


def _sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None)


def _insert_event(engine: Engine) -> int:
    with engine.begin() as connection:
        return int(
            connection.execute(
                text(
                    "INSERT INTO audit_events (event_type, details) "
                    "VALUES ('auth.login_failed', '{\"reason\": \"invalid_credentials\"}') "
                    "RETURNING id"
                )
            ).scalar_one()
        )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_events SET details = '{}'::jsonb WHERE id = :id",
        "DELETE FROM audit_events WHERE id = :id",
    ],
)
def test_db_07_audit_events_are_append_only(migrator_engine: Engine, statement: str) -> None:
    event_id = _insert_event(migrator_engine)
    with pytest.raises(DBAPIError) as raised, migrator_engine.begin() as connection:
        connection.execute(text(statement), {"id": event_id})
    assert _sqlstate(raised.value) == RESTRICT_VIOLATION
    with migrator_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM audit_events")).scalar_one() == 1
