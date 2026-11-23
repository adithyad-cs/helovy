"""E-13 ``GET /api/v1/templates?doc_type=invoice`` (docs/07 §4)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError
from app.core.routing import HeadAwareRoute
from app.modules.rendering import catalogue
from app.modules.tenancy.dependencies import Tenant, current_tenant

router = APIRouter(prefix="/api/v1/templates", tags=["templates"], route_class=HeadAwareRoute)


@router.get("")
def list_templates(
    tenant: Annotated[Tenant, Depends(current_tenant)],
    db: Annotated[Session, Depends(get_db)],
    doc_type: Annotated[str, Query()] = "invoice",
) -> JSONResponse:
    if doc_type != "invoice":
        raise AppError(
            "validation_failed",
            detail="1 field needs attention.",
            errors=[{"pointer": "/doc_type", "code": "invalid_choice", "message": "Use invoice."}],
        )
    items = [catalogue.template_json(t) for t in catalogue.list_active(db, doc_type)]
    return JSONResponse({"items": items})
