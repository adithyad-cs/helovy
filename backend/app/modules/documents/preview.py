"""E-20 draft preview (docs/07 §4; docs/09 §13): a watermarked PDF built from the current
draft, rendered in a worker; nothing is stored and no audit event is written."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.validation import state_name
from app.modules.businesses.models import Business
from app.modules.customers.models import Customer
from app.modules.documents import drafts
from app.modules.documents.snapshot import build_payload
from app.modules.rendering.pool import RenderError, RenderJob, RenderPool

logger = logging.getLogger("app.documents")


def preview_payload(db: Session, org_id: uuid.UUID, document_id: uuid.UUID) -> dict[str, Any]:
    with db.begin():
        document = drafts.find_document(db, org_id, document_id)
        if document.status != "draft":
            raise AppError("document_not_draft")
        lines = drafts.draft_lines(db, document.id)
        if not lines:
            raise drafts.field_problem("/lines", "no_lines", "Add at least one line to preview.")
        business = db.get(Business, document.business_id)
        customer = db.get(Customer, document.customer_id)
        if business is None or customer is None:  # guarded by the composite foreign keys
            raise AppError("not_found")
        result = drafts.calculate([drafts.line_input(line) for line in lines])
        return build_payload(
            document=document,
            business=business,
            business_state_name=state_name(business.state_code),
            customer=customer,
            customer_state_name=state_name(customer.state_code),
            lines=lines,
            result=result,
            number=None,
            financial_year=None,
            issue_date=None,
            finalized_at=None,
        )


def render_preview(pool: RenderPool, payload: dict[str, Any]) -> bytes:
    template_id = str(payload["document"]["template_id"])
    try:
        return pool.render(RenderJob(template_id=template_id, payload=payload, preview=True))
    except RenderError as error:
        if error.code in ("render_timeout", "unavailable"):
            raise AppError("dependency_unavailable", detail="The PDF service is busy.") from None
        logger.error("preview render failed: %s", error.code)
        raise AppError("internal_error") from None
