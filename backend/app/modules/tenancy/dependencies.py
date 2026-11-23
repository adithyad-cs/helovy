"""The current-organization dependency and scope helpers (docs/04 §3, §8; docs/07 §1.11).

The organization always comes from the session, never from a request (mandatory decision 3).
The auth module resolves the session and stores a ``Tenant`` on ``request.state``; this module
only reads it, so tenant modules (businesses, customers, documents) never import auth.
A request without a resolved tenant is refused (fail closed).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Request

from app.core.errors import AppError
from app.modules.tenancy.models import OWNER


@dataclass(frozen=True)
class Tenant:
    org_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    session_id: uuid.UUID


def set_tenant(request: Request, tenant: Tenant) -> None:
    request.state.tenant = tenant
    # Read by the access log line (docs/12 §10): identifiers only, never personal data.
    request.state.log_org_id = str(tenant.org_id)
    request.state.log_user_id = str(tenant.user_id)


def current_tenant(request: Request) -> Tenant:
    """The session's organization and user; 401 without a session, 403 for another role."""
    tenant = getattr(request.state, "tenant", None)
    if not isinstance(tenant, Tenant):
        raise AppError("unauthenticated")
    if tenant.role != OWNER:
        raise AppError("forbidden_role")  # unreachable in P0-Lite: every member is an owner
    return tenant


def parse_uuid(value: str) -> uuid.UUID:
    """A path ID as a UUID; a malformed ID is 404 ``not_found``, never 422 (docs/07 §1.4)."""
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise AppError("not_found") from None
    if str(parsed) != value.lower():
        raise AppError("not_found")  # only the canonical hyphenated form is an ID
    return parsed
