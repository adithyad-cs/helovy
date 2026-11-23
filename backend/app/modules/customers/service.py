"""Customer service (docs/07 E-09 to E-12). Every customer is resolved inside its business,
which is resolved inside the session's organization; misses are 404 (docs/04 §8).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.http import Cursor, check_version, encode_cursor
from app.core.schemas import rfc3339
from app.core.validation import state_name
from app.modules.audit.service import record_event
from app.modules.businesses.service import find_business
from app.modules.customers.models import Customer
from app.modules.customers.schemas import FIELDS
from app.modules.tenancy.dependencies import Tenant


def to_json(customer: Customer) -> dict[str, Any]:
    """The Customer representation (docs/07 §3.2)."""
    return {
        "id": str(customer.id),
        "display_name": customer.display_name,
        "contact_name": customer.contact_name,
        "email": customer.email,
        "phone": customer.phone,
        "address_line1": customer.address_line1,
        "address_line2": customer.address_line2,
        "city": customer.city,
        "state_code": customer.state_code,
        "state_name": state_name(customer.state_code),
        "postal_code": customer.postal_code,
        "country_code": customer.country_code,
        "gstin": customer.gstin,
        "version": customer.version,
        "created_at": rfc3339(customer.created_at),
        "updated_at": rfc3339(customer.updated_at),
    }


def to_summary(customer: Customer) -> dict[str, Any]:
    """The list item (docs/07 §3.2): id, display_name, contact_name, email, city, created_at."""
    return {
        "id": str(customer.id),
        "display_name": customer.display_name,
        "contact_name": customer.contact_name,
        "email": customer.email,
        "city": customer.city,
        "created_at": rfc3339(customer.created_at),
    }


def _check_gstin_state(gstin: str | None, state_code: str | None) -> None:
    if gstin and state_code and gstin[:2] != state_code:
        raise AppError(
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


def cursor_scope(business_id: uuid.UUID) -> str:
    return f"customers:{business_id}"


def find_customer(
    db: Session, org_id: uuid.UUID, business_id: uuid.UUID, customer_id: uuid.UUID
) -> Customer:
    """A customer of the organization's business, or 404 (also used by documents)."""
    customer = db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.business_id == business_id,
            Customer.org_id == org_id,
        )
    ).scalar_one_or_none()
    if customer is None:
        raise AppError("not_found")
    return customer


def list_customers(
    db: Session,
    org_id: uuid.UUID,
    business_id: uuid.UUID,
    *,
    csrf_key: bytes,
    prefix: str | None,
    limit: int,
    after: Cursor | None,
) -> dict[str, Any]:
    """Newest first (created_at DESC, id DESC), optional case-insensitive name prefix."""
    with db.begin():
        find_business(db, org_id, business_id)
        query = select(Customer).where(
            Customer.business_id == business_id, Customer.org_id == org_id
        )
        if prefix:
            escaped = prefix.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(func.lower(Customer.display_name).like(escaped + "%", escape="\\"))
        if after is not None:
            query = query.where(
                or_(
                    Customer.created_at < after.created_at,
                    and_(Customer.created_at == after.created_at, Customer.id < after.id),
                )
            )
        rows = list(
            db.execute(
                query.order_by(Customer.created_at.desc(), Customer.id.desc()).limit(limit + 1)
            ).scalars()
        )
    page, more = rows[:limit], len(rows) > limit
    next_cursor = (
        encode_cursor(csrf_key, cursor_scope(business_id), page[-1].created_at, page[-1].id)
        if more
        else None
    )
    return {"items": [to_summary(c) for c in page], "next_cursor": next_cursor}


def get_customer(
    db: Session, org_id: uuid.UUID, business_id: uuid.UUID, customer_id: uuid.UUID
) -> Customer:
    with db.begin():
        find_business(db, org_id, business_id)
        return find_customer(db, org_id, business_id, customer_id)


def create_customer(
    db: Session, tenant: Tenant, business_id: uuid.UUID, *, now: datetime, fields: dict[str, Any]
) -> Customer:
    with db.begin():
        find_business(db, tenant.org_id, business_id)
        _check_gstin_state(fields.get("gstin"), fields.get("state_code"))
        values = {name: fields.get(name) for name in FIELDS if name != "country_code"}
        customer = Customer(
            org_id=tenant.org_id,
            business_id=business_id,
            country_code=fields.get("country_code") or "IN",
            created_at=now,
            updated_at=now,
            **values,
        )
        db.add(customer)
        db.flush()
        record_event(
            db,
            "customer.created",
            occurred_at=now,
            org_id=tenant.org_id,
            actor_user_id=tenant.user_id,
            subject_type="customer",
            subject_id=customer.id,
            details={"fields": sorted(n for n in FIELDS if values.get(n) is not None)},
        )
    return customer


def update_customer(
    db: Session,
    tenant: Tenant,
    business_id: uuid.UUID,
    customer_id: uuid.UUID,
    *,
    now: datetime,
    expected_version: int,
    changes: dict[str, Any],
) -> Customer:
    with db.begin():
        find_business(db, tenant.org_id, business_id)
        customer = db.execute(
            select(Customer)
            .where(
                Customer.id == customer_id,
                Customer.business_id == business_id,
                Customer.org_id == tenant.org_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if customer is None:
            raise AppError("not_found")
        check_version(expected_version, customer.version)
        changed = sorted(n for n, v in changes.items() if getattr(customer, n) != v)
        _check_gstin_state(
            changes.get("gstin", customer.gstin), changes.get("state_code", customer.state_code)
        )
        if not changed:
            return customer
        for name in changed:
            setattr(customer, name, changes[name])
        customer.version += 1
        customer.updated_at = now
        db.flush()
        record_event(
            db,
            "customer.updated",
            occurred_at=now,
            org_id=tenant.org_id,
            actor_user_id=tenant.user_id,
            subject_type="customer",
            subject_id=customer.id,
            details={"fields": changed},
        )
    return customer
