"""Document endpoints: E-14, E-15, E-17, E-18, E-19 (docs/07 §4). More arrive in M4-M6."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.db import get_db
from app.core.http import etag, require_if_match
from app.core.routing import HeadAwareRoute
from app.core.schemas import require_json_body
from app.modules.businesses.service import get_business
from app.modules.documents import drafts
from app.modules.documents.schemas import CalculateRequest, DocumentCreate, DocumentPatch
from app.modules.tenancy.dependencies import Tenant, current_tenant, parse_uuid

business_router = APIRouter(
    prefix="/api/v1/businesses/{business_id}",
    tags=["documents"],
    route_class=HeadAwareRoute,
    dependencies=[Depends(require_json_body)],
)
router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
    route_class=HeadAwareRoute,
    dependencies=[Depends(require_json_body)],
)


def document_response(body: dict[str, Any], status_code: int = 200) -> JSONResponse:
    headers = {"ETag": etag(int(body["version"]))}
    if status_code == 201:
        headers["Location"] = f"/api/v1/documents/{body['id']}"
    return JSONResponse(body, status_code=status_code, headers=headers)


@business_router.post("/calculate")
def calculate(
    business_id: str,
    body: CalculateRequest,
    request: Request,
    tenant: Annotated[Tenant, Depends(current_tenant)],
    db: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> JSONResponse:
    """E-14: stateless server calculation; 60 per minute per session (docs/07 §1.9)."""
    get_business(db, tenant.org_id, parse_uuid(business_id))
    request.app.state.rate_limits["calculate"].check(str(tenant.session_id), clock.now())
    result = drafts.calculate([line.calc_input() for line in body.lines])
    return JSONResponse(drafts.calculation_json(result))


@business_router.post("/documents")
def create_document(
    business_id: str,
    body: DocumentCreate,
    tenant: Annotated[Tenant, Depends(current_tenant)],
    db: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> JSONResponse:
    created = drafts.create_draft(
        db, tenant, parse_uuid(business_id), now=clock.now(), fields=body.provided()
    )
    return document_response(created, 201)


@router.get("/{document_id}")
def get_document(
    document_id: str,
    tenant: Annotated[Tenant, Depends(current_tenant)],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    return document_response(
        drafts.get_draft_or_document(db, tenant.org_id, parse_uuid(document_id))
    )


@router.patch("/{document_id}")
def update_document(
    document_id: str,
    body: DocumentPatch,
    request: Request,
    tenant: Annotated[Tenant, Depends(current_tenant)],
    db: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> JSONResponse:
    target = parse_uuid(document_id)
    expected = require_if_match(request)
    updated = drafts.update_draft(
        db, tenant, target, now=clock.now(), expected_version=expected, changes=body.provided()
    )
    return document_response(updated)


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    request: Request,
    tenant: Annotated[Tenant, Depends(current_tenant)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    target = parse_uuid(document_id)
    expected = require_if_match(request)
    drafts.delete_draft(db, tenant, target, expected_version=expected)
    return Response(status_code=204)
