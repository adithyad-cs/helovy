"""Recording audit events and counting sign-in failures (docs/06 §9; docs/12 §2.2, §12).

``details`` holds non-sensitive context only: never passwords, tokens, idempotency keys,
emails, addresses or amounts other than the finalised number (docs/06 §9). The caller owns
the transaction, so an event commits or rolls back together with the change it describes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Literal

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.core.logging import request_id_var
from app.modules.audit.models import AuditEvent

EventType = Literal[
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
]
SubjectType = Literal["user", "organization", "business", "customer", "document"]

LOGIN_FAILED = "auth.login_failed"
THROTTLED_REASON = "throttled"


def record_event(
    db: Session,
    event_type: EventType,
    *,
    occurred_at: datetime,
    org_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    subject_type: SubjectType | None = None,
    subject_id: uuid.UUID | None = None,
    subject_hash: str | None = None,
    ip: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Insert one event inside the caller's transaction, tagged with the request ID."""
    db.execute(
        insert(AuditEvent).values(
            event_type=event_type,
            occurred_at=occurred_at,
            org_id=org_id,
            actor_user_id=actor_user_id,
            subject_type=subject_type,
            subject_id=subject_id,
            subject_hash=subject_hash,
            ip=ip,
            request_id=request_id_var.get(),
            details=details or {},
        )
    )


def recent_login_failures(
    db: Session,
    *,
    now: datetime,
    window: timedelta,
    subject_hash: str | None = None,
    ip: str | None = None,
) -> list[datetime]:
    """Times of counted sign-in failures inside the window, oldest first.

    Exactly one of ``subject_hash`` or ``ip`` selects the key (docs/12 §2.2). Attempts that
    were refused because of throttling are recorded but not counted, so a lock-out lasts
    15 minutes from the real failures instead of growing with every refused attempt.
    """
    if (subject_hash is None) == (ip is None):
        raise ValueError("pass exactly one of subject_hash or ip")
    key = AuditEvent.subject_hash == subject_hash if subject_hash else AuditEvent.ip == ip
    rows = db.execute(
        select(AuditEvent.occurred_at)
        .where(
            AuditEvent.event_type == LOGIN_FAILED,
            key,
            AuditEvent.occurred_at > now - window,
            AuditEvent.occurred_at <= now,
            func.coalesce(AuditEvent.details["reason"].astext, "") != THROTTLED_REASON,
        )
        .order_by(AuditEvent.occurred_at)
    ).scalars()
    return list(rows)
