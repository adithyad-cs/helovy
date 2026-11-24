"""E-16 document history (docs/07 §3.4, E-16; docs/08 §18).

The one cross-module read allowed by docs/04 §3 rule 5: the list joins ``customers`` (current
name for drafts) and ``document_snapshots`` (issued buyer name and grand total for finalised
documents) read-only. Order is ``created_at DESC, id DESC`` with signed cursors.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.core.http import Cursor, encode_cursor
from app.core.schemas import rfc3339
from app.modules.businesses.service import find_business
from app.modules.calc import engine
from app.modules.customers.models import Customer
from app.modules.documents.models import Document, DocumentArtifact, DocumentSnapshot


def cursor_scope(business_id: uuid.UUID) -> str:
    return f"documents:{business_id}"


def _escape(prefix: str) -> str:
    return prefix.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def list_documents(
    db: Session,
    org_id: uuid.UUID,
    business_id: uuid.UUID,
    *,
    csrf_key: bytes,
    status: str | None,
    prefix: str | None,
    limit: int,
    after: Cursor | None,
) -> dict[str, Any]:
    shown_name = case(
        (Document.status == "finalized", DocumentSnapshot.buyer_name),
        else_=Customer.display_name,
    )
    query = (
        select(
            Document.id,
            Document.status,
            Document.document_number,
            Document.issue_date,
            Document.created_at,
            Document.updated_at,
            shown_name.label("customer_name"),
            DocumentSnapshot.grand_total,
            DocumentArtifact.status.label("pdf_status"),
        )
        .join(Customer, Customer.id == Document.customer_id)
        .outerjoin(DocumentSnapshot, DocumentSnapshot.document_id == Document.id)
        .outerjoin(
            DocumentArtifact,
            and_(DocumentArtifact.document_id == Document.id, DocumentArtifact.kind == "final_pdf"),
        )
        .where(Document.business_id == business_id, Document.org_id == org_id)
    )
    if status is not None:
        query = query.where(Document.status == status)
    if prefix:
        pattern = _escape(prefix)
        query = query.where(
            or_(
                func.lower(Document.document_number).like(pattern, escape="\\"),
                func.lower(shown_name).like(pattern, escape="\\"),
            )
        )
    if after is not None:
        query = query.where(
            or_(
                Document.created_at < after.created_at,
                and_(Document.created_at == after.created_at, Document.id < after.id),
            )
        )
    with db.begin():
        find_business(db, org_id, business_id)
        rows = db.execute(
            query.order_by(Document.created_at.desc(), Document.id.desc()).limit(limit + 1)
        ).all()
    page, more = rows[:limit], len(rows) > limit
    items = [
        {
            "id": str(row.id),
            "status": row.status,
            "number": row.document_number,
            "customer_name": row.customer_name,
            "issue_date": row.issue_date.isoformat() if row.issue_date else None,
            "grand_total": (
                engine.money_str(row.grand_total)
                if row.status == "finalized" and row.grand_total is not None
                else None
            ),
            "pdf_status": row.pdf_status if row.status == "finalized" else None,
            "created_at": rfc3339(row.created_at),
            "updated_at": rfc3339(row.updated_at),
        }
        for row in page
    ]
    next_cursor = (
        encode_cursor(csrf_key, cursor_scope(business_id), page[-1].created_at, page[-1].id)
        if more
        else None
    )
    return {"items": items, "next_cursor": next_cursor}
