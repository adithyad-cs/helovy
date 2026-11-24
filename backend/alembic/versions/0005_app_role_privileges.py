"""0005_app_role_privileges: schema USAGE and database CONNECT for ps5_app, set by migration.

Revision ID: 0005_app_role_privileges
Revises: 0004_issuance

Written by hand for the Render staging preparation (docs/DEPLOYMENT_RENDER.md), following the
role model of docs/06 §11: ``ps5_migrator`` owns the database and runs every migration;
``ps5_app`` is the restricted runtime role.

Locally, ``deploy/postgres/init`` gives ``ps5_app`` CONNECT on the databases and USAGE on their
``public`` schema when the volume is first created. A managed server (Render Postgres) has no
init script, so these privileges must come from a migration that the database owner can run:

- ``GRANT USAGE ON SCHEMA public TO ps5_app``: the owner of ``public`` is
  ``pg_database_owner`` (PostgreSQL 15+), that is the migrator.
- ``GRANT CONNECT ON DATABASE <current database> TO ps5_app``: the database name is taken from
  ``current_database()``, so the same migration works on ``ps5``, ``ps5_test`` and a name
  that Render suffixes.
- ``REVOKE CREATE ON SCHEMA public FROM PUBLIC``: already the PostgreSQL 15+ default and done
  by the local init script; repeated here so no role can create objects in ``public``.

The privileges of PUBLIC on the database (CONNECT, TEMPORARY) and its USAGE on ``public`` are
deliberately not revoked here: the local init script revokes them, but on a managed platform
its own monitoring roles may rely on them. Table privileges stay in each migration (06 §11).

The upgrade first refuses to continue when ``ps5_app`` is missing or is not a restricted role
(superuser, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS, or a member of the migrating role).
The downgrade changes nothing: removing CONNECT or USAGE would lock the application out of a
database that was created with them (the local init script grants them too).
"""

from __future__ import annotations

import re

from alembic import op

revision = "0005_app_role_privileges"
down_revision = "0004_issuance"
branch_labels = None
depends_on = None

APP_ROLE = "ps5_app"
_ROLE_NAME = re.compile(r"[a-z_][a-z0-9_]{0,62}")


def restricted_role_guard(role: str) -> str:
    """SQL that raises unless ``role`` exists and is a restricted login role.

    ``role`` is a fixed identifier from this module or a test, never user input, and must be a
    plain lower-case PostgreSQL identifier.
    """
    if not _ROLE_NAME.fullmatch(role):
        raise ValueError("role must be a plain lower-case identifier")
    literal = role
    return f"""
        DO $guard$
        DECLARE
            r record;
        BEGIN
            SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls,
                   rolcanlogin
              INTO r FROM pg_roles WHERE rolname = '{literal}';
            IF NOT FOUND THEN
                RAISE EXCEPTION 'role % does not exist: create it before migrating',
                    quote_literal('{literal}')
                    USING ERRCODE = 'undefined_object';
            END IF;
            IF r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
               OR r.rolbypassrls OR NOT r.rolcanlogin THEN
                RAISE EXCEPTION 'role % must be a restricted login role (no SUPERUSER, '
                    'CREATEDB, CREATEROLE, REPLICATION or BYPASSRLS)', quote_literal('{literal}')
                    USING ERRCODE = 'insufficient_privilege';
            END IF;
            IF pg_has_role('{literal}', current_user, 'MEMBER') THEN
                RAISE EXCEPTION 'role % must not be a member of the migrating role %',
                    quote_literal('{literal}'), quote_ident(current_user)
                    USING ERRCODE = 'insufficient_privilege';
            END IF;
        END
        $guard$
    """  # noqa: S608 - a validated identifier, never user input


def upgrade() -> None:
    op.execute(restricted_role_guard(APP_ROLE))
    op.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    op.execute(
        f"""
        DO $grant$
        BEGIN
            EXECUTE format('GRANT CONNECT ON DATABASE %I TO {APP_ROLE}', current_database());
        END
        $grant$
        """
    )


def downgrade() -> None:
    # Intentionally empty: see the module docstring.
    pass
