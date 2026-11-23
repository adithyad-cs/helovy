"""Business profile service (docs/07 E-06 to E-08). ``org_id`` always comes from the session.

Every lookup is ``WHERE id = :id AND org_id = :org``; a miss is 404 whether the record is
missing or belongs to another organization (docs/04 §8). Edits lock the row, check the
version from ``If-Match`` and increment it, in one transaction (docs/07 §1.6).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.http import check_version
from app.core.schemas import rfc3339
from app.core.validation import state_name
from app.modules.audit.service import record_event
from app.modules.businesses.models import Business
from app.modules.businesses.schemas import FIELDS
from app.modules.tenancy.dependencies import Tenant


def to_json(business: Business) -> dict[str, Any]:
    """The Business representation (docs/07 §3.1); ``state_name`` is derived, not stored."""
    return {
        "id": str(business.id),
        "legal_name": business.legal_name,
        "trade_name": business.trade_name,
        "address_line1": business.address_line1,
        "address_line2": business.address_line2,
        "city": business.city,
        "state_code": business.state_code,
        "state_name": state_name(business.state_code),
        "postal_code": business.postal_code,
        "country_code": business.country_code,
        "phone": business.phone,
        "email": business.email,
        "gstin": business.gstin,
        "version": business.version,
        "created_at": rfc3339(business.created_at),
        "updated_at": rfc3339(business.updated_at),
    }


def _state_mismatch() -> AppError:
    return AppError(
        "validation_failed",
        detail="1 field needs attention.",
        errors=[
            {
                "pointer": "/gstin",
                "code": "state_mismatch",
                "message": "The first two digits of the GSTIN must match the state code.",
            }
        ],
    )


def _check_gstin_state(gstin: str | None, state_code: str | None) -> None:
    if gstin and state_code and gstin[:2] != state_code:
        raise _state_mismatch()


def find_business(db: Session, org_id: uuid.UUID, business_id: uuid.UUID) -> Business:
    """The organization's business by ID, or 404 (also used by customers and documents)."""
    business = db.execute(
        select(Business).where(Business.id == business_id, Business.org_id == org_id)
    ).scalar_one_or_none()
    if business is None:
        raise AppError("not_found")
    return business


def get_business(db: Session, org_id: uuid.UUID, business_id: uuid.UUID) -> Business:
    with db.begin():
        return find_business(db, org_id, business_id)


def summary_for_org(db: Session, org_id: uuid.UUID) -> dict[str, str] | None:
    """``{"id", "legal_name"}`` of the organization's business, for E-03 and E-05."""
    with db.begin():
        row = db.execute(
            select(Business.id, Business.legal_name).where(Business.org_id == org_id)
        ).first()
    return {"id": str(row.id), "legal_name": row.legal_name} if row else None


def create_business(
    db: Session, tenant: Tenant, *, now: datetime, fields: dict[str, Any]
) -> Business:
    _check_gstin_state(fields.get("gstin"), fields.get("state_code"))
    values = {name: fields.get(name) for name in FIELDS if name != "country_code"}
    business = Business(
        org_id=tenant.org_id,
        country_code=fields.get("country_code") or "IN",
        created_at=now,
        updated_at=now,
        **values,
    )
    try:
        with db.begin():
            exists = db.execute(
                select(Business.id).where(Business.org_id == tenant.org_id)
            ).scalar_one_or_none()
            if exists is not None:
                raise AppError("business_already_exists")
            db.add(business)
            db.flush()
            record_event(
                db,
                "business.created",
                occurred_at=now,
                org_id=tenant.org_id,
                actor_user_id=tenant.user_id,
                subject_type="business",
                subject_id=business.id,
                details={"fields": sorted(n for n in FIELDS if values.get(n) is not None)},
            )
    except IntegrityError as exc:  # a concurrent create: businesses_one_per_org_uq
        raise AppError("business_already_exists") from exc
    return business


def update_business(
    db: Session,
    tenant: Tenant,
    business_id: uuid.UUID,
    *,
    now: datetime,
    expected_version: int,
    changes: dict[str, Any],
) -> Business:
    with db.begin():
        business = db.execute(
            select(Business)
            .where(Business.id == business_id, Business.org_id == tenant.org_id)
            .with_for_update()
        ).scalar_one_or_none()
        if business is None:
            raise AppError("not_found")
        check_version(expected_version, business.version)
        changed = sorted(
            name for name, value in changes.items() if getattr(business, name) != value
        )
        merged_gstin = changes.get("gstin", business.gstin)
        merged_state = changes.get("state_code", business.state_code)
        _check_gstin_state(merged_gstin, merged_state)
        if not changed:
            return business  # nothing to save: same version and ETag, no audit event
        for name in changed:
            setattr(business, name, changes[name])
        business.version += 1
        business.updated_at = now
        db.flush()
        record_event(
            db,
            "business.updated",
            occurred_at=now,
            org_id=tenant.org_id,
            actor_user_id=tenant.user_id,
            subject_type="business",
            subject_id=business.id,
            details={"fields": changed},
        )
    return business
