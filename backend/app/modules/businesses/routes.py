"""E-06 ``POST /api/v1/businesses``, E-07 ``GET`` and E-08 ``PATCH /api/v1/businesses/{id}``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.db import get_db
from app.core.http import etag, require_if_match
from app.core.routing import HeadAwareRoute
from app.core.schemas import require_json_body
from app.modules.businesses import service
from app.modules.businesses.models import Business
from app.modules.businesses.schemas import BusinessCreate, BusinessPatch
from app.modules.tenancy.dependencies import Tenant, current_tenant, parse_uuid

router = APIRouter(
    prefix="/api/v1/businesses",
    tags=["businesses"],
    route_class=HeadAwareRoute,
    dependencies=[Depends(require_json_body)],
)


def _response(business: Business, status_code: int = 200) -> JSONResponse:
    headers = {"ETag": etag(business.version)}
    if status_code == 201:
        headers["Location"] = f"/api/v1/businesses/{business.id}"
    return JSONResponse(service.to_json(business), status_code=status_code, headers=headers)


@router.post("")
def create_business(
    body: BusinessCreate,
    tenant: Annotated[Tenant, Depends(current_tenant)],
    db: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> JSONResponse:
    business = service.create_business(db, tenant, now=clock.now(), fields=body.provided())
    return _response(business, 201)


@router.get("/{business_id}")
def get_business(
    business_id: str,
    tenant: Annotated[Tenant, Depends(current_tenant)],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    return _response(service.get_business(db, tenant.org_id, parse_uuid(business_id)))


@router.patch("/{business_id}")
def update_business(
    business_id: str,
    body: BusinessPatch,
    request: Request,
    tenant: Annotated[Tenant, Depends(current_tenant)],
    db: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> JSONResponse:
    target = parse_uuid(business_id)
    expected = require_if_match(request)
    business = service.update_business(
        db, tenant, target, now=clock.now(), expected_version=expected, changes=body.provided()
    )
    return _response(business)
