"""E-09 to E-12: ``/api/v1/businesses/{business_id}/customers[/{customer_id}]``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.db import get_db
from app.core.errors import AppError
from app.core.http import decode_cursor, etag, require_if_match
from app.core.routing import HeadAwareRoute
from app.core.schemas import require_json_body
from app.modules.customers import service
from app.modules.customers.models import Customer
from app.modules.customers.schemas import CustomerCreate, CustomerPatch
from app.modules.tenancy.dependencies import Tenant, current_tenant, parse_uuid

router = APIRouter(
    prefix="/api/v1/businesses/{business_id}/customers",
    tags=["customers"],
    route_class=HeadAwareRoute,
    dependencies=[Depends(require_json_body)],
)

SEARCH_MAX = 100


def _response(business_id: str, customer: Customer, status_code: int = 200) -> JSONResponse:
    headers = {"ETag": etag(customer.version)}
    if status_code == 201:
        headers["Location"] = f"/api/v1/businesses/{business_id}/customers/{customer.id}"
    return JSONResponse(service.to_json(customer), status_code=status_code, headers=headers)


def _search_prefix(q: str | None) -> str | None:
    """``q``: 1-100 characters, trimmed; an empty value means no search (docs/09 §4.3)."""
    if q is None or not q.strip():
        return None
    prefix = q.strip()
    if len(prefix) > SEARCH_MAX:
        raise AppError(
            "validation_failed",
            detail="1 field needs attention.",
            errors=[
                {
                    "pointer": "/q",
                    "code": "too_long",
                    "message": f"Use at most {SEARCH_MAX} characters.",
                }
            ],
        )
    return prefix


@router.get("")
def list_customers(
    business_id: str,
    request: Request,
    tenant: Annotated[Tenant, Depends(current_tenant)],
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query()] = None,
) -> JSONResponse:
    target = parse_uuid(business_id)
    key = request.app.state.settings.csrf_key
    after = decode_cursor(key, service.cursor_scope(target), cursor) if cursor else None
    page = service.list_customers(
        db, tenant.org_id, target, csrf_key=key, prefix=_search_prefix(q), limit=limit, after=after
    )
    return JSONResponse(page)


@router.post("")
def create_customer(
    business_id: str,
    body: CustomerCreate,
    tenant: Annotated[Tenant, Depends(current_tenant)],
    db: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> JSONResponse:
    target = parse_uuid(business_id)
    customer = service.create_customer(db, tenant, target, now=clock.now(), fields=body.provided())
    return _response(str(target), customer, 201)


@router.get("/{customer_id}")
def get_customer(
    business_id: str,
    customer_id: str,
    tenant: Annotated[Tenant, Depends(current_tenant)],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    business, customer = parse_uuid(business_id), parse_uuid(customer_id)
    return _response(str(business), service.get_customer(db, tenant.org_id, business, customer))


@router.patch("/{customer_id}")
def update_customer(
    business_id: str,
    customer_id: str,
    body: CustomerPatch,
    request: Request,
    tenant: Annotated[Tenant, Depends(current_tenant)],
    db: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> JSONResponse:
    business, target = parse_uuid(business_id), parse_uuid(customer_id)
    expected = require_if_match(request)
    customer = service.update_customer(
        db,
        tenant,
        business,
        target,
        now=clock.now(),
        expected_version=expected,
        changes=body.provided(),
    )
    return _response(str(business), customer)
