"""0004_issuance: stored_files, document_snapshots, document_artifacts, idempotency_keys.

Revision ID: 0004_issuance
Revises: 0003_documents

Written by hand and reviewed against docs/06 §3.11-§3.14, §7, §8, §10, §11 and §12. Every
name that docs/06 gives is reproduced exactly; unnamed checks use ``<table>_<column>_ck``.
"""

from __future__ import annotations

from alembic import op

revision = "0004_issuance"
down_revision = "0003_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE stored_files (
            id uuid NOT NULL DEFAULT gen_random_uuid(),
            org_id uuid NOT NULL,
            purpose text NOT NULL DEFAULT 'document_pdf',
            bucket text NOT NULL,
            object_key text NOT NULL,
            content_type text NOT NULL DEFAULT 'application/pdf',
            size_bytes bigint NOT NULL,
            sha256 text NOT NULL,
            object_version_id text,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT stored_files_pkey PRIMARY KEY (id),
            CONSTRAINT stored_files_org_fk FOREIGN KEY (org_id)
                REFERENCES organizations (id) ON DELETE RESTRICT,
            CONSTRAINT stored_files_purpose_ck CHECK (purpose = 'document_pdf'),
            CONSTRAINT stored_files_object_key_ck
                CHECK (object_key LIKE 'orgs/' || org_id::text || '/%'),
            CONSTRAINT stored_files_content_type_ck CHECK (content_type = 'application/pdf'),
            CONSTRAINT stored_files_size_bytes_ck CHECK (size_bytes > 0 AND size_bytes <= 20971520),
            CONSTRAINT stored_files_sha256_ck CHECK (sha256 ~ '^[0-9a-f]{64}$'),
            CONSTRAINT stored_files_bucket_key_uq UNIQUE (bucket, object_key),
            CONSTRAINT stored_files_id_org_uq UNIQUE (id, org_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE document_snapshots (
            id uuid NOT NULL DEFAULT gen_random_uuid(),
            org_id uuid NOT NULL,
            document_id uuid NOT NULL,
            schema_version text NOT NULL DEFAULT 'snapshot-1',
            calc_version text NOT NULL,
            tax_rule_set text NOT NULL DEFAULT 'none',
            template_id text NOT NULL,
            payload jsonb NOT NULL,
            canonical_sha256 text NOT NULL,
            buyer_name text GENERATED ALWAYS AS (payload #>> '{buyer,display_name}') STORED,
            grand_total numeric(16,2)
                GENERATED ALWAYS AS ((payload #>> '{totals,grand_total}')::numeric(16,2)) STORED,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT document_snapshots_pkey PRIMARY KEY (id),
            CONSTRAINT document_snapshots_document_fk FOREIGN KEY (document_id, org_id)
                REFERENCES documents (id, org_id) ON DELETE RESTRICT,
            CONSTRAINT document_snapshots_template_fk FOREIGN KEY (template_id)
                REFERENCES templates (id) ON DELETE RESTRICT,
            CONSTRAINT document_snapshots_document_uq UNIQUE (document_id),
            CONSTRAINT document_snapshots_schema_version_ck
                CHECK (schema_version ~ '^snapshot-[0-9]+$'),
            CONSTRAINT document_snapshots_calc_version_ck
                CHECK (calc_version ~ '^calc-[0-9]+\\.[0-9]+\\.[0-9]+$'),
            CONSTRAINT document_snapshots_tax_rule_set_ck CHECK (tax_rule_set = 'none'),
            CONSTRAINT document_snapshots_canonical_sha256_ck
                CHECK (canonical_sha256 ~ '^[0-9a-f]{64}$')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE document_artifacts (
            id uuid NOT NULL DEFAULT gen_random_uuid(),
            org_id uuid NOT NULL,
            document_id uuid NOT NULL,
            kind text NOT NULL DEFAULT 'final_pdf',
            status text NOT NULL DEFAULT 'pending',
            attempts smallint NOT NULL DEFAULT 0,
            last_error_code text,
            template_id text NOT NULL,
            template_sha256 text,
            renderer_version text,
            stored_file_id uuid,
            rendered_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT document_artifacts_pkey PRIMARY KEY (id),
            CONSTRAINT document_artifacts_document_fk FOREIGN KEY (document_id, org_id)
                REFERENCES documents (id, org_id) ON DELETE RESTRICT,
            CONSTRAINT document_artifacts_file_fk FOREIGN KEY (stored_file_id, org_id)
                REFERENCES stored_files (id, org_id) ON DELETE RESTRICT,
            CONSTRAINT document_artifacts_template_fk FOREIGN KEY (template_id)
                REFERENCES templates (id) ON DELETE RESTRICT,
            CONSTRAINT document_artifacts_document_kind_uq UNIQUE (document_id, kind),
            CONSTRAINT document_artifacts_kind_ck CHECK (kind = 'final_pdf'),
            CONSTRAINT document_artifacts_status_ck
                CHECK (status IN ('pending', 'ready', 'failed')),
            CONSTRAINT document_artifacts_attempts_ck CHECK (attempts BETWEEN 0 AND 100),
            CONSTRAINT document_artifacts_last_error_code_ck CHECK (
                last_error_code IN ('render_error', 'render_timeout', 'storage_error',
                                    'snapshot_integrity')
            ),
            CONSTRAINT document_artifacts_template_sha256_ck
                CHECK (template_sha256 ~ '^[0-9a-f]{64}$'),
            CONSTRAINT document_artifacts_renderer_version_ck
                CHECK (char_length(renderer_version) <= 40),
            CONSTRAINT document_artifacts_ready_ck CHECK (
                status <> 'ready' OR (stored_file_id IS NOT NULL AND rendered_at IS NOT NULL
                                      AND template_sha256 IS NOT NULL
                                      AND renderer_version IS NOT NULL)
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX document_artifacts_open_idx ON document_artifacts (status, updated_at) "
        "WHERE status <> 'ready'"
    )
    op.execute(
        """
        CREATE TABLE idempotency_keys (
            org_id uuid NOT NULL,
            scope text NOT NULL,
            idem_key text NOT NULL,
            request_fingerprint text NOT NULL,
            status text NOT NULL DEFAULT 'in_progress',
            response_status smallint,
            response_body jsonb,
            resource_id uuid,
            user_id uuid NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL,
            CONSTRAINT idempotency_keys_pkey PRIMARY KEY (org_id, scope, idem_key),
            CONSTRAINT idempotency_keys_org_fk FOREIGN KEY (org_id)
                REFERENCES organizations (id) ON DELETE RESTRICT,
            CONSTRAINT idempotency_keys_user_fk FOREIGN KEY (user_id)
                REFERENCES users (id) ON DELETE RESTRICT,
            CONSTRAINT idempotency_keys_scope_ck CHECK (scope = 'document.finalize'),
            CONSTRAINT idempotency_keys_idem_key_ck CHECK (idem_key ~ '^[A-Za-z0-9_-]{8,128}$'),
            CONSTRAINT idempotency_keys_request_fingerprint_ck
                CHECK (request_fingerprint ~ '^[0-9a-f]{64}$'),
            CONSTRAINT idempotency_keys_status_ck CHECK (status IN ('in_progress', 'completed')),
            CONSTRAINT idempotency_keys_completed_ck CHECK (
                status = 'in_progress'
                OR (response_status IS NOT NULL AND response_body IS NOT NULL)
            )
        )
        """
    )
    op.execute("CREATE INDEX idempotency_keys_expires_idx ON idempotency_keys (expires_at)")

    # docs/06 §10: trigger functions raise SQLSTATE 23001 (restrict_violation).
    op.execute(
        """
        CREATE FUNCTION document_snapshots_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'document snapshots are immutable'
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_document_snapshots_immutable
            BEFORE UPDATE OR DELETE ON document_snapshots
            FOR EACH ROW EXECUTE FUNCTION document_snapshots_immutable()
        """
    )
    op.execute(
        """
        CREATE FUNCTION document_artifacts_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'document artifacts cannot be deleted'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            IF OLD.status = 'ready' THEN
                RAISE EXCEPTION 'a ready artifact cannot be changed'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            IF NEW.org_id IS DISTINCT FROM OLD.org_id
               OR NEW.document_id IS DISTINCT FROM OLD.document_id
               OR NEW.kind IS DISTINCT FROM OLD.kind
               OR NEW.template_id IS DISTINCT FROM OLD.template_id THEN
                RAISE EXCEPTION 'org_id, document_id, kind and template_id cannot change'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_document_artifacts_guard
            BEFORE UPDATE OR DELETE ON document_artifacts
            FOR EACH ROW EXECUTE FUNCTION document_artifacts_guard()
        """
    )

    # docs/06 §11.
    op.execute("GRANT SELECT, INSERT ON document_snapshots, stored_files TO ps5_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON document_artifacts, idempotency_keys TO ps5_app")


def downgrade() -> None:
    # Development and test databases only (docs/06 §14, rule 5).
    op.execute("DROP TABLE idempotency_keys")
    op.execute("DROP TABLE document_artifacts")
    op.execute("DROP FUNCTION document_artifacts_guard()")
    op.execute("DROP TABLE document_snapshots")
    op.execute("DROP FUNCTION document_snapshots_immutable()")
    op.execute("DROP TABLE stored_files")
