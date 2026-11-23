"""0003_documents: templates (+ classic@1), number_series, documents, document_lines (docs/06 §14).

Revision ID: 0003_documents
Revises: 0002_parties

Written by hand and reviewed against docs/06 §3.7-§3.10, §6, §10, §11 and §12. Every name
that docs/06 gives is reproduced exactly; unnamed checks use ``<table>_<column>_ck``.
"""

from __future__ import annotations

from alembic import op

revision = "0003_documents"
down_revision = "0002_parties"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE templates (
            id text NOT NULL,
            code text NOT NULL,
            version integer NOT NULL,
            doc_type text NOT NULL,
            name text NOT NULL,
            description text NOT NULL,
            tier text NOT NULL DEFAULT 'free',
            is_active boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT templates_pkey PRIMARY KEY (id),
            CONSTRAINT templates_code_version_uq UNIQUE (code, version),
            CONSTRAINT templates_id_ck CHECK (id = code || '@' || version::text),
            CONSTRAINT templates_code_ck CHECK (code ~ '^[a-z][a-z0-9-]{1,30}$'),
            CONSTRAINT templates_version_ck CHECK (version >= 1),
            CONSTRAINT templates_doc_type_ck CHECK (doc_type = 'invoice'),
            CONSTRAINT templates_tier_ck CHECK (tier = 'free')
        )
        """
    )
    op.execute(
        """
        INSERT INTO templates (id, code, version, doc_type, name, description, tier, is_active)
        VALUES ('classic@1', 'classic', 1, 'invoice', 'Classic',
                'A clean, traditional A4 invoice layout.', 'free', true)
        """
    )
    op.execute(
        """
        CREATE TABLE number_series (
            id uuid NOT NULL DEFAULT gen_random_uuid(),
            org_id uuid NOT NULL,
            business_id uuid NOT NULL,
            doc_type text NOT NULL DEFAULT 'invoice',
            financial_year text NOT NULL,
            prefix text NOT NULL DEFAULT 'INV',
            next_seq integer NOT NULL DEFAULT 1,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT number_series_pkey PRIMARY KEY (id),
            CONSTRAINT number_series_business_fk FOREIGN KEY (business_id, org_id)
                REFERENCES businesses (id, org_id) ON DELETE RESTRICT,
            CONSTRAINT number_series_scope_uq UNIQUE (business_id, doc_type, financial_year),
            CONSTRAINT number_series_id_business_uq UNIQUE (id, business_id),
            CONSTRAINT number_series_doc_type_ck CHECK (doc_type = 'invoice'),
            CONSTRAINT number_series_financial_year_ck
                CHECK (financial_year ~ '^[0-9]{2}-[0-9]{2}$'),
            CONSTRAINT number_series_prefix_ck CHECK (prefix = 'INV'),
            CONSTRAINT number_series_next_seq_ck CHECK (next_seq BETWEEN 1 AND 1000000)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE documents (
            id uuid NOT NULL DEFAULT gen_random_uuid(),
            org_id uuid NOT NULL,
            business_id uuid NOT NULL,
            customer_id uuid NOT NULL,
            doc_type text NOT NULL DEFAULT 'invoice',
            status text NOT NULL DEFAULT 'draft',
            tax_mode text NOT NULL DEFAULT 'no_tax',
            template_id text NOT NULL DEFAULT 'classic@1',
            currency text NOT NULL DEFAULT 'INR',
            reference text,
            due_date date,
            notes text,
            terms text,
            number_series_id uuid,
            sequence_no integer,
            document_number text,
            issue_date date,
            finalized_at timestamptz,
            finalized_by uuid,
            version integer NOT NULL DEFAULT 1,
            created_by uuid NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT documents_pkey PRIMARY KEY (id),
            CONSTRAINT documents_business_fk FOREIGN KEY (business_id, org_id)
                REFERENCES businesses (id, org_id) ON DELETE RESTRICT,
            CONSTRAINT documents_customer_fk FOREIGN KEY (customer_id, business_id)
                REFERENCES customers (id, business_id) ON DELETE RESTRICT,
            CONSTRAINT documents_series_fk FOREIGN KEY (number_series_id, business_id)
                REFERENCES number_series (id, business_id) ON DELETE RESTRICT,
            CONSTRAINT documents_template_fk FOREIGN KEY (template_id)
                REFERENCES templates (id) ON DELETE RESTRICT,
            CONSTRAINT documents_finalized_by_fk FOREIGN KEY (finalized_by)
                REFERENCES users (id) ON DELETE RESTRICT,
            CONSTRAINT documents_created_by_fk FOREIGN KEY (created_by)
                REFERENCES users (id) ON DELETE RESTRICT,
            CONSTRAINT documents_doc_type_ck CHECK (doc_type = 'invoice'),
            CONSTRAINT documents_status_ck CHECK (status IN ('draft', 'finalized')),
            CONSTRAINT documents_tax_mode_ck CHECK (tax_mode = 'no_tax'),
            CONSTRAINT documents_currency_ck CHECK (currency = 'INR'),
            CONSTRAINT documents_reference_ck CHECK (char_length(reference) <= 100),
            CONSTRAINT documents_notes_ck CHECK (char_length(notes) <= 2000),
            CONSTRAINT documents_terms_ck CHECK (char_length(terms) <= 2000),
            CONSTRAINT documents_sequence_no_ck CHECK (sequence_no >= 1),
            CONSTRAINT documents_document_number_ck CHECK (char_length(document_number) <= 16),
            CONSTRAINT documents_version_ck CHECK (version >= 1),
            CONSTRAINT documents_state_ck CHECK (
                (status = 'draft' AND number_series_id IS NULL AND sequence_no IS NULL
                   AND document_number IS NULL AND issue_date IS NULL
                   AND finalized_at IS NULL AND finalized_by IS NULL)
                OR
                (status = 'finalized' AND number_series_id IS NOT NULL AND sequence_no IS NOT NULL
                   AND document_number IS NOT NULL AND issue_date IS NOT NULL
                   AND finalized_at IS NOT NULL AND finalized_by IS NOT NULL)
            ),
            CONSTRAINT documents_due_date_ck
                CHECK (due_date IS NULL OR issue_date IS NULL OR due_date >= issue_date),
            CONSTRAINT documents_number_uq UNIQUE (business_id, doc_type, document_number),
            CONSTRAINT documents_series_seq_uq UNIQUE (number_series_id, sequence_no),
            CONSTRAINT documents_id_org_uq UNIQUE (id, org_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX documents_business_created_idx "
        "ON documents (business_id, created_at DESC, id DESC)"
    )
    op.execute(
        "CREATE INDEX documents_business_status_created_idx "
        "ON documents (business_id, status, created_at DESC, id DESC)"
    )
    op.execute("CREATE INDEX documents_customer_idx ON documents (customer_id)")
    op.execute(
        """
        CREATE TABLE document_lines (
            id uuid NOT NULL DEFAULT gen_random_uuid(),
            org_id uuid NOT NULL,
            document_id uuid NOT NULL,
            position smallint NOT NULL,
            description text NOT NULL,
            quantity numeric(12,3) NOT NULL,
            unit text,
            unit_price numeric(14,2) NOT NULL,
            discount_type text NOT NULL DEFAULT 'none',
            discount_value numeric(14,2),
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT document_lines_pkey PRIMARY KEY (id),
            CONSTRAINT document_lines_document_fk FOREIGN KEY (document_id, org_id)
                REFERENCES documents (id, org_id) ON DELETE CASCADE,
            CONSTRAINT document_lines_position_uq UNIQUE (document_id, position),
            CONSTRAINT document_lines_position_ck CHECK (position BETWEEN 1 AND 200),
            CONSTRAINT document_lines_description_ck
                CHECK (char_length(description) BETWEEN 1 AND 500),
            CONSTRAINT document_lines_quantity_ck CHECK (quantity > 0 AND quantity <= 1000000),
            CONSTRAINT document_lines_unit_ck CHECK (char_length(unit) <= 20),
            CONSTRAINT document_lines_unit_price_ck
                CHECK (unit_price >= 0 AND unit_price <= 10000000),
            CONSTRAINT document_lines_discount_type_ck
                CHECK (discount_type IN ('none', 'percent', 'amount')),
            CONSTRAINT document_lines_discount_ck CHECK (
                (discount_type = 'none'    AND discount_value IS NULL)
                OR (discount_type = 'percent' AND discount_value > 0 AND discount_value <= 100)
                OR (discount_type = 'amount'  AND discount_value > 0
                                              AND discount_value <= round(quantity * unit_price, 2))
            )
        )
        """
    )

    # docs/06 §10: trigger functions raise SQLSTATE 23001 (restrict_violation).
    op.execute(
        """
        CREATE FUNCTION documents_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF OLD.status = 'finalized' THEN
                    RAISE EXCEPTION 'finalised documents cannot be deleted'
                        USING ERRCODE = 'restrict_violation';
                END IF;
                RETURN OLD;
            END IF;
            IF OLD.status = 'finalized' THEN
                RAISE EXCEPTION 'finalised documents cannot be changed'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            IF NEW.org_id IS DISTINCT FROM OLD.org_id
               OR NEW.business_id IS DISTINCT FROM OLD.business_id
               OR NEW.doc_type IS DISTINCT FROM OLD.doc_type THEN
                RAISE EXCEPTION 'org_id, business_id and doc_type cannot change'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_documents_guard
            BEFORE UPDATE OR DELETE ON documents
            FOR EACH ROW EXECUTE FUNCTION documents_guard()
        """
    )
    op.execute(
        """
        CREATE FUNCTION document_lines_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            parent_id uuid;
            parent_status text;
        BEGIN
            IF TG_OP = 'INSERT' THEN
                parent_id := NEW.document_id;
            ELSIF TG_OP = 'UPDATE' THEN
                parent_id := COALESCE(NEW.document_id, OLD.document_id);
            ELSE
                parent_id := OLD.document_id;
            END IF;
            SELECT status INTO parent_status FROM documents WHERE id = parent_id;
            -- A missing parent is allowed: during the cascade from deleting a draft, the
            -- parent row is already gone (docs/06 §10).
            IF parent_status = 'finalized' THEN
                RAISE EXCEPTION 'lines of finalised documents cannot be changed'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_document_lines_guard
            BEFORE INSERT OR UPDATE OR DELETE ON document_lines
            FOR EACH ROW EXECUTE FUNCTION document_lines_guard()
        """
    )

    # docs/06 §11.
    op.execute("GRANT SELECT ON templates TO ps5_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON number_series TO ps5_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON documents, document_lines TO ps5_app")


def downgrade() -> None:
    # Development and test databases only (docs/06 §14, rule 5).
    op.execute("DROP TABLE document_lines")
    op.execute("DROP FUNCTION document_lines_guard()")
    op.execute("DROP TABLE documents")
    op.execute("DROP FUNCTION documents_guard()")
    op.execute("DROP TABLE number_series")
    op.execute("DROP TABLE templates")
