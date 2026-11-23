"""0002_parties: businesses and customers (docs/06 §14).

Revision ID: 0002_parties
Revises: 0001_identity

Written by hand and reviewed against docs/06 §3.5, §3.6, §4, §11 and §12. Every name that
docs/06 gives is reproduced exactly; unnamed checks use ``<table>_<column>_ck``.
"""

from __future__ import annotations

from alembic import op

revision = "0002_parties"
down_revision = "0001_identity"
branch_labels = None
depends_on = None

GSTIN_PATTERN = "^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE businesses (
            id uuid NOT NULL DEFAULT gen_random_uuid(),
            org_id uuid NOT NULL,
            legal_name text NOT NULL,
            trade_name text,
            address_line1 text NOT NULL,
            address_line2 text,
            city text NOT NULL,
            state_code text NOT NULL,
            postal_code text NOT NULL,
            country_code text NOT NULL DEFAULT 'IN',
            phone text,
            email text,
            gstin text,
            version integer NOT NULL DEFAULT 1,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT businesses_pkey PRIMARY KEY (id),
            CONSTRAINT businesses_org_fk FOREIGN KEY (org_id)
                REFERENCES organizations (id) ON DELETE RESTRICT,
            CONSTRAINT businesses_one_per_org_uq UNIQUE (org_id),
            CONSTRAINT businesses_id_org_uq UNIQUE (id, org_id),
            CONSTRAINT businesses_legal_name_ck CHECK (char_length(legal_name) BETWEEN 1 AND 200),
            CONSTRAINT businesses_trade_name_ck CHECK (char_length(trade_name) <= 200),
            CONSTRAINT businesses_address_line1_ck
                CHECK (char_length(address_line1) BETWEEN 1 AND 200),
            CONSTRAINT businesses_address_line2_ck CHECK (char_length(address_line2) <= 200),
            CONSTRAINT businesses_city_ck CHECK (char_length(city) BETWEEN 1 AND 100),
            CONSTRAINT businesses_state_code_ck CHECK (state_code ~ '^[0-9]{{2}}$'),
            CONSTRAINT businesses_postal_code_ck CHECK (postal_code ~ '^[1-9][0-9]{{5}}$'),
            CONSTRAINT businesses_country_code_ck CHECK (country_code = 'IN'),
            CONSTRAINT businesses_phone_ck CHECK (phone ~ '^[0-9+() -]{{6,20}}$'),
            CONSTRAINT businesses_email_ck CHECK (char_length(email) <= 254),
            CONSTRAINT businesses_gstin_ck CHECK (
                gstin ~ '{GSTIN_PATTERN}' AND substr(gstin, 1, 2) = state_code
            ),
            CONSTRAINT businesses_version_ck CHECK (version >= 1)
        )
        """
    )
    op.execute(
        f"""
        CREATE TABLE customers (
            id uuid NOT NULL DEFAULT gen_random_uuid(),
            org_id uuid NOT NULL,
            business_id uuid NOT NULL,
            display_name text NOT NULL,
            contact_name text,
            email text,
            phone text,
            address_line1 text,
            address_line2 text,
            city text,
            state_code text,
            postal_code text,
            country_code text NOT NULL DEFAULT 'IN',
            gstin text,
            version integer NOT NULL DEFAULT 1,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT customers_pkey PRIMARY KEY (id),
            CONSTRAINT customers_business_fk FOREIGN KEY (business_id, org_id)
                REFERENCES businesses (id, org_id) ON DELETE RESTRICT,
            CONSTRAINT customers_id_business_uq UNIQUE (id, business_id),
            CONSTRAINT customers_display_name_ck
                CHECK (char_length(display_name) BETWEEN 1 AND 200),
            CONSTRAINT customers_contact_name_ck CHECK (char_length(contact_name) <= 120),
            CONSTRAINT customers_email_ck CHECK (char_length(email) <= 254),
            CONSTRAINT customers_phone_ck CHECK (phone ~ '^[0-9+() -]{{6,20}}$'),
            CONSTRAINT customers_address_line1_ck CHECK (char_length(address_line1) <= 200),
            CONSTRAINT customers_address_line2_ck CHECK (char_length(address_line2) <= 200),
            CONSTRAINT customers_city_ck CHECK (char_length(city) <= 100),
            CONSTRAINT customers_state_code_ck CHECK (state_code ~ '^[0-9]{{2}}$'),
            CONSTRAINT customers_postal_code_ck CHECK (postal_code ~ '^[1-9][0-9]{{5}}$'),
            CONSTRAINT customers_country_code_ck CHECK (country_code = 'IN'),
            CONSTRAINT customers_gstin_ck CHECK (
                gstin ~ '{GSTIN_PATTERN}'
                AND (state_code IS NULL OR substr(gstin, 1, 2) = state_code)
            ),
            CONSTRAINT customers_version_ck CHECK (version >= 1)
        )
        """
    )
    op.execute(
        "CREATE INDEX customers_business_name_idx "
        "ON customers (business_id, lower(display_name) text_pattern_ops)"
    )
    op.execute(
        "CREATE INDEX customers_business_created_idx "
        "ON customers (business_id, created_at DESC, id DESC)"
    )

    # docs/06 §11: SELECT, INSERT, UPDATE for the app role; never DELETE, TRUNCATE or DDL.
    op.execute("GRANT SELECT, INSERT, UPDATE ON businesses, customers TO ps5_app")


def downgrade() -> None:
    # Development and test databases only (docs/06 §14, rule 5).
    op.execute("DROP TABLE customers")
    op.execute("DROP TABLE businesses")
