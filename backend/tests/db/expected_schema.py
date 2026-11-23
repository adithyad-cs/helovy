"""Every constraint, index and trigger name that docs/06 gives, per migration (DB-01).

Each milestone adds its migration's names here, copied from docs/06 §3, §10 and §12.
"""

from __future__ import annotations

# 0001_identity (M1): docs/06 §3.1-§3.4, §3.15, §10.
IDENTITY_CONSTRAINTS = {
    "organizations_pkey",
    "memberships_pkey",
    "sessions_token_hash_uq",
    "sessions_membership_fk",
}
IDENTITY_INDEXES = {
    "users_email_lower_uq",
    "memberships_user_idx",
    "sessions_user_idx",
    "sessions_expires_idx",
    "audit_events_org_time_idx",
    "audit_events_subject_idx",
    "audit_events_login_subject_idx",
    "audit_events_login_ip_idx",
}
IDENTITY_TRIGGERS = {"trg_audit_events_append_only"}
IDENTITY_TABLES = {"organizations", "users", "memberships", "sessions", "audit_events"}

# 0002_parties (M2): docs/06 §3.5, §3.6, §12.
PARTIES_CONSTRAINTS = {
    "businesses_one_per_org_uq",
    "businesses_id_org_uq",
    "customers_business_fk",
    "customers_id_business_uq",
}
PARTIES_INDEXES = {"customers_business_name_idx", "customers_business_created_idx"}
PARTIES_TABLES = {"businesses", "customers"}

TABLES = IDENTITY_TABLES | PARTIES_TABLES
CONSTRAINTS = IDENTITY_CONSTRAINTS | PARTIES_CONSTRAINTS
INDEXES = IDENTITY_INDEXES | PARTIES_INDEXES
TRIGGERS = IDENTITY_TRIGGERS
