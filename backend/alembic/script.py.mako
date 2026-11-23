"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}

Written by hand and reviewed against docs/06 (rule 1 of docs/06 §14): checks, triggers and
grants are explicit SQL with the exact documented names.
"""

from __future__ import annotations

from alembic import op

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = None
depends_on = None


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    # Development and test databases only (docs/06 §14, rule 5).
    ${downgrades if downgrades else "pass"}
