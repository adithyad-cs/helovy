"""0001_identity: organizations, users, memberships, sessions, audit_events (docs/06 §14).

Revision ID: 0001_identity
Revises: (none)

Written by hand and reviewed against docs/06 §3.1-§3.4, §3.15, §10 and §11. Every name that
docs/06 gives is reproduced exactly. Constraints that docs/06 describes without a name use
the pattern ``<table>_<column>_ck`` / ``<table>_<column>_fk`` (recorded in PROGRESS.md).
"""

from __future__ import annotations

from alembic import op

revision = "0001_identity"
down_revision = None
branch_labels = None
depends_on = None

AUDIT_EVENT_TYPES = (
    "account.created",
    "auth.login_succeeded",
    "auth.login_failed",
    "auth.logout",
    "business.created",
    "business.updated",
    "customer.created",
    "customer.updated",
    "document.finalized",
    "document.pdf_rendered",
    "document.pdf_render_failed",
    "document.pdf_downloaded",
)


def upgrade() -> None:
    event_types = ", ".join(f"'{name}'" for name in AUDIT_EVENT_TYPES)
    op.execute(
        """
        CREATE TABLE organizations (
            id uuid NOT NULL DEFAULT gen_random_uuid(),
            name text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT organizations_pkey PRIMARY KEY (id),
            CONSTRAINT organizations_name_ck CHECK (char_length(name) BETWEEN 1 AND 200)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE users (
            id uuid NOT NULL DEFAULT gen_random_uuid(),
            email text NOT NULL,
            password_hash text NOT NULL,
            display_name text NOT NULL,
            is_active boolean NOT NULL DEFAULT true,
            last_login_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT users_pkey PRIMARY KEY (id),
            CONSTRAINT users_email_ck CHECK (char_length(email) BETWEEN 3 AND 254),
            CONSTRAINT users_password_hash_ck CHECK (password_hash LIKE '$argon2id$%'),
            CONSTRAINT users_display_name_ck CHECK (char_length(display_name) BETWEEN 1 AND 120)
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX users_email_lower_uq ON users (lower(email))")
    op.execute(
        """
        CREATE TABLE memberships (
            org_id uuid NOT NULL,
            user_id uuid NOT NULL,
            role text NOT NULL DEFAULT 'owner',
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT memberships_pkey PRIMARY KEY (org_id, user_id),
            CONSTRAINT memberships_org_fk FOREIGN KEY (org_id)
                REFERENCES organizations (id) ON DELETE RESTRICT,
            CONSTRAINT memberships_user_fk FOREIGN KEY (user_id)
                REFERENCES users (id) ON DELETE RESTRICT,
            CONSTRAINT memberships_role_ck CHECK (role = 'owner')
        )
        """
    )
    op.execute("CREATE INDEX memberships_user_idx ON memberships (user_id)")
    op.execute(
        """
        CREATE TABLE sessions (
            id uuid NOT NULL DEFAULT gen_random_uuid(),
            token_hash bytea NOT NULL,
            org_id uuid NOT NULL,
            user_id uuid NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            last_seen_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL,
            revoked_at timestamptz,
            ip inet,
            user_agent text,
            CONSTRAINT sessions_pkey PRIMARY KEY (id),
            CONSTRAINT sessions_token_hash_uq UNIQUE (token_hash),
            CONSTRAINT sessions_token_hash_ck CHECK (octet_length(token_hash) = 32),
            CONSTRAINT sessions_membership_fk FOREIGN KEY (org_id, user_id)
                REFERENCES memberships (org_id, user_id) ON DELETE CASCADE,
            CONSTRAINT sessions_user_agent_ck CHECK (char_length(user_agent) <= 256)
        )
        """
    )
    op.execute("CREATE INDEX sessions_user_idx ON sessions (user_id)")
    op.execute("CREATE INDEX sessions_expires_idx ON sessions (expires_at)")
    op.execute(
        f"""
        CREATE TABLE audit_events (
            id bigint GENERATED ALWAYS AS IDENTITY,
            org_id uuid,
            actor_user_id uuid,
            event_type text NOT NULL,
            subject_type text,
            subject_id uuid,
            subject_hash text,
            ip inet,
            request_id text,
            details jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            occurred_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT audit_events_pkey PRIMARY KEY (id),
            CONSTRAINT audit_events_org_fk FOREIGN KEY (org_id)
                REFERENCES organizations (id) ON DELETE RESTRICT,
            CONSTRAINT audit_events_actor_user_fk FOREIGN KEY (actor_user_id)
                REFERENCES users (id) ON DELETE RESTRICT,
            CONSTRAINT audit_events_event_type_ck CHECK (event_type IN ({event_types})),
            CONSTRAINT audit_events_subject_type_ck CHECK (
                subject_type IN ('user', 'organization', 'business', 'customer', 'document')
            ),
            CONSTRAINT audit_events_subject_hash_ck CHECK (subject_hash ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT audit_events_request_id_ck CHECK (char_length(request_id) <= 64)
        )
        """
    )
    op.execute("CREATE INDEX audit_events_org_time_idx ON audit_events (org_id, occurred_at DESC)")
    op.execute(
        "CREATE INDEX audit_events_subject_idx "
        "ON audit_events (subject_type, subject_id, occurred_at)"
    )
    op.execute(
        "CREATE INDEX audit_events_login_subject_idx ON audit_events (subject_hash, occurred_at) "
        "WHERE event_type = 'auth.login_failed'"
    )
    op.execute(
        "CREATE INDEX audit_events_login_ip_idx ON audit_events (ip, occurred_at) "
        "WHERE event_type = 'auth.login_failed'"
    )

    # docs/06 §10: every trigger function raises SQLSTATE 23001 (restrict_violation).
    op.execute(
        """
        CREATE FUNCTION audit_events_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only'
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_events_append_only
            BEFORE UPDATE OR DELETE ON audit_events
            FOR EACH ROW EXECUTE FUNCTION audit_events_append_only()
        """
    )

    # docs/06 §11: explicit grants on the tables this migration creates; never TRUNCATE,
    # REFERENCES, TRIGGER or DDL. The identity sequence of audit_events needs no grant
    # (verified by DB-08 in tests/db/test_grants.py: ps5_app inserts audit events without it).
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON organizations, users, memberships, sessions TO ps5_app"
    )
    op.execute("GRANT SELECT, INSERT ON audit_events TO ps5_app")


def downgrade() -> None:
    # Development and test databases only (docs/06 §14, rule 5).
    op.execute("DROP TABLE audit_events")
    op.execute("DROP FUNCTION audit_events_append_only()")
    op.execute("DROP TABLE sessions")
    op.execute("DROP TABLE memberships")
    op.execute("DROP TABLE users")
    op.execute("DROP TABLE organizations")
