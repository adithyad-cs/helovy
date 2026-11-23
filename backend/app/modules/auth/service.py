"""Accounts, sign-in, sessions and sign-out (docs/04 §7; docs/07 E-03 to E-05; docs/12 §2, §4).

Argon2 work happens outside database transactions, so no transaction is held open while a
password is verified. Every outcome writes its audit event in the same transaction as the
change it describes.
"""

from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.modules.audit.service import recent_login_failures, record_event
from app.modules.auth import security
from app.modules.auth.models import User, UserSession
from app.modules.tenancy.models import OWNER, Membership, Organization

logger = logging.getLogger("app.auth")

SESSION_IDLE = timedelta(hours=24)
SESSION_ABSOLUTE = timedelta(days=7)
LAST_SEEN_REFRESH = timedelta(minutes=1)
THROTTLE_WINDOW = timedelta(minutes=15)
THROTTLE_LIMIT = 5
USER_AGENT_MAX = 256
PASSWORD_MIN = 12
PASSWORD_MAX = 1024


class AccountExistsError(Exception):
    """An account with this email already exists."""


@dataclass(frozen=True)
class SessionContext:
    session_id: uuid.UUID
    org_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    email: str
    display_name: str
    org_name: str
    expires_at: datetime


@dataclass(frozen=True)
class LoginResult:
    token: str
    context: SessionContext


def create_account(
    db: Session,
    *,
    now: datetime,
    email: str,
    display_name: str,
    org_name: str,
    password: str,
) -> tuple[uuid.UUID, uuid.UUID]:
    """One organization, one user and an owner membership in one transaction (docs/05 §8).

    Returns ``(org_id, user_id)``. Raises AccountExistsError for an existing email.
    """
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        raise ValueError(f"the password must be {PASSWORD_MIN}-{PASSWORD_MAX} characters")
    password_hash = security.hash_password(password)
    normalised = security.normalise_email(email)
    try:
        with db.begin():
            exists = db.execute(
                select(User.id).where(func.lower(User.email) == normalised)
            ).scalar_one_or_none()
            if exists is not None:
                raise AccountExistsError(normalised)
            org = Organization(name=org_name)
            user = User(email=normalised, password_hash=password_hash, display_name=display_name)
            db.add_all([org, user])
            db.flush()
            db.add(Membership(org_id=org.id, user_id=user.id, role=OWNER))
            db.flush()
            record_event(
                db,
                "account.created",
                occurred_at=now,
                org_id=org.id,
                actor_user_id=user.id,
                subject_type="user",
                subject_id=user.id,
                details={"via": "cli"},
            )
    except IntegrityError as exc:  # a concurrent create of the same email
        raise AccountExistsError(normalised) from exc
    return org.id, user.id


def _retry_after(failures: list[datetime], now: datetime) -> int:
    """Seconds until fewer than THROTTLE_LIMIT failures remain in the window; 0 if allowed."""
    if len(failures) < THROTTLE_LIMIT:
        return 0
    pivot = failures[len(failures) - THROTTLE_LIMIT]
    return max(1, math.ceil((pivot + THROTTLE_WINDOW - now).total_seconds()))


def _record_failure(
    db: Session, *, now: datetime, subject_hash: str, ip: str | None, reason: str
) -> None:
    with db.begin():
        record_event(
            db,
            "auth.login_failed",
            occurred_at=now,
            subject_hash=subject_hash,
            ip=ip,
            details={"reason": reason},
        )


def login(
    db: Session,
    settings: Settings,
    *,
    now: datetime,
    email: str,
    password: str,
    ip: str | None,
    user_agent: str | None,
    presented_token: str | None,
) -> LoginResult:
    """E-03 behaviour: throttle → verify → revoke the presented session → new session."""
    normalised = security.normalise_email(email)
    subject_hash = security.login_subject_hash(settings.csrf_key, normalised)

    with db.begin():
        waits = [
            _retry_after(
                recent_login_failures(
                    db, now=now, window=THROTTLE_WINDOW, subject_hash=subject_hash
                ),
                now,
            )
        ]
        if ip is not None:
            waits.append(
                _retry_after(recent_login_failures(db, now=now, window=THROTTLE_WINDOW, ip=ip), now)
            )
        retry_after = max(waits)
        if retry_after:
            record_event(
                db,
                "auth.login_failed",
                occurred_at=now,
                subject_hash=subject_hash,
                ip=ip,
                details={"reason": "throttled"},
            )
    if retry_after:
        raise AppError("rate_limited", headers={"Retry-After": str(retry_after)})

    with db.begin():
        row = db.execute(
            select(User, Membership, Organization)
            .outerjoin(Membership, Membership.user_id == User.id)
            .outerjoin(Organization, Organization.id == Membership.org_id)
            .where(func.lower(User.email) == normalised)
            .order_by(Membership.created_at)
            .limit(1)
        ).first()

    if row is None:
        security.dummy_verify(password)
        _record_failure(db, now=now, subject_hash=subject_hash, ip=ip, reason="invalid_credentials")
        raise AppError("invalid_credentials")
    user: User = row[0]
    membership: Membership | None = row[1]  # outer joins: may be missing
    org: Organization | None = row[2]
    if not security.verify_password(user.password_hash, password):
        _record_failure(db, now=now, subject_hash=subject_hash, ip=ip, reason="invalid_credentials")
        raise AppError("invalid_credentials")
    if not user.is_active:
        _record_failure(db, now=now, subject_hash=subject_hash, ip=ip, reason="inactive")
        raise AppError("invalid_credentials")
    if membership is None or org is None:
        logger.warning("sign-in refused: user has no membership", extra={"user_id": str(user.id)})
        _record_failure(db, now=now, subject_hash=subject_hash, ip=ip, reason="invalid_credentials")
        raise AppError("invalid_credentials")

    rehash = security.hash_password(password) if security.needs_rehash(user.password_hash) else None
    token = security.new_session_token()
    expires_at = now + SESSION_ABSOLUTE
    with db.begin():
        if presented_token:
            # Session fixation: any session presented with the request ends here (docs/12 §2.2).
            db.execute(
                update(UserSession)
                .where(
                    UserSession.token_hash == security.hash_session_token(presented_token),
                    UserSession.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
        session_row = UserSession(
            token_hash=security.hash_session_token(token),
            org_id=membership.org_id,
            user_id=user.id,
            created_at=now,
            last_seen_at=now,
            expires_at=expires_at,
            ip=ip,
            user_agent=user_agent[:USER_AGENT_MAX] if user_agent else None,
        )
        db.add(session_row)
        values: dict[str, object] = {"last_login_at": now, "updated_at": now}
        if rehash is not None:
            values["password_hash"] = rehash
        db.execute(update(User).where(User.id == user.id).values(**values))
        db.flush()
        record_event(
            db,
            "auth.login_succeeded",
            occurred_at=now,
            org_id=membership.org_id,
            actor_user_id=user.id,
            subject_type="user",
            subject_id=user.id,
            ip=ip,
        )
    context = SessionContext(
        session_id=session_row.id,
        org_id=membership.org_id,
        user_id=user.id,
        role=membership.role,
        email=user.email,
        display_name=user.display_name,
        org_name=org.name,
        expires_at=expires_at,
    )
    return LoginResult(token=token, context=context)


def resolve_session(db: Session, *, now: datetime, token: str) -> SessionContext | None:
    """The session for a cookie token, if it is valid now (docs/04 §7, steps 1-4).

    Valid means: not revoked, before the absolute expiry, used within the idle window and
    owned by an active user. ``last_seen_at`` is refreshed at most once a minute.
    """
    token_hash = security.hash_session_token(token)
    with db.begin():
        row = db.execute(
            select(UserSession, User, Membership, Organization)
            .join(User, User.id == UserSession.user_id)
            .join(
                Membership,
                (Membership.org_id == UserSession.org_id)
                & (Membership.user_id == UserSession.user_id),
            )
            .join(Organization, Organization.id == UserSession.org_id)
            .where(UserSession.token_hash == token_hash)
        ).first()
        if row is None:
            return None
        session_row, user, membership, org = row._tuple()
        if (
            session_row.revoked_at is not None
            or now >= session_row.expires_at
            or now >= session_row.last_seen_at + SESSION_IDLE
            or not user.is_active
        ):
            return None
        if now - session_row.last_seen_at >= LAST_SEEN_REFRESH:
            db.execute(
                update(UserSession).where(UserSession.id == session_row.id).values(last_seen_at=now)
            )
    return SessionContext(
        session_id=session_row.id,
        org_id=session_row.org_id,
        user_id=user.id,
        role=membership.role,
        email=user.email,
        display_name=user.display_name,
        org_name=org.name,
        expires_at=session_row.expires_at,
    )


def logout(db: Session, *, now: datetime, context: SessionContext, ip: str | None) -> None:
    """E-04: revoke the session and record ``auth.logout``."""
    with db.begin():
        db.execute(
            update(UserSession)
            .where(UserSession.id == context.session_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        record_event(
            db,
            "auth.logout",
            occurred_at=now,
            org_id=context.org_id,
            actor_user_id=context.user_id,
            subject_type="user",
            subject_id=context.user_id,
            ip=ip,
        )


def session_id_for_token(db: Session, token: str) -> uuid.UUID | None:
    """The ID of the session row for a token, whatever its state (used by the CSRF check)."""
    with db.begin():
        return db.execute(
            select(UserSession.id).where(
                UserSession.token_hash == security.hash_session_token(token)
            )
        ).scalar_one_or_none()
