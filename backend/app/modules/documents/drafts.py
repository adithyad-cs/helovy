"""Draft invoices (docs/07 E-14, E-15, E-17 to E-19; docs/09 §9).

Drafts store inputs only; every read recomputes lines and totals with ``calc-1.0.0``.
Edits lock the document row (FOR UPDATE), check the status and the If-Match version, replace
the whole line set when ``lines`` is present, and increment ``version``, in one transaction.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.http import check_version
from app.core.schemas import rfc3339
from app.modules.businesses.service import find_business
from app.modules.calc import engine
from app.modules.calc.engine import CalcError
from app.modules.customers.models import Customer
from app.modules.customers.service import find_customer
from app.modules.documents.models import Document, DocumentLine
from app.modules.documents.schemas import DocumentLineIn
from app.modules.rendering.catalogue import find_template
from app.modules.tenancy.dependencies import Tenant


def field_problem(pointer: str, code: str, message: str) -> AppError:
    return AppError(
        "validation_failed",
        detail="1 field needs attention.",
        errors=[{"pointer": pointer, "code": code, "message": message}],
    )


def calculate(lines: Sequence[engine.LineInput]) -> engine.DocumentResult:
    """``calc-1.0.0`` with ``total_too_large`` reported at ``/lines`` (E-14, saves)."""
    try:
        return engine.calculate_document(lines)
    except CalcError as error:
        raise field_problem("/lines", error.code, error.message) from None


def calculation_json(result: engine.DocumentResult) -> dict[str, Any]:
    return {
        "calc_version": engine.CALC_VERSION,
        "lines": [
            {
                "position": index,
                "gross": engine.money_str(line.gross),
                "discount": engine.money_str(line.discount),
                "line_total": engine.money_str(line.line_total),
            }
            for index, line in enumerate(result.lines, start=1)
        ],
        "totals": totals_json(result.totals),
    }


def totals_json(totals: engine.Totals) -> dict[str, str]:
    return {
        "gross_total": engine.money_str(totals.gross_total),
        "discount_total": engine.money_str(totals.discount_total),
        "grand_total": engine.money_str(totals.grand_total),
    }


def line_input(line: DocumentLine) -> engine.LineInput:
    kind = line.discount_type
    if kind not in engine.DISCOUNT_TYPES:  # guarded by document_lines_discount_type_ck
        raise ValueError(f"unexpected discount type {kind!r}")
    return engine.LineInput(line.quantity, line.unit_price, kind, line.discount_value)


def draft_lines(db: Session, document_id: uuid.UUID) -> list[DocumentLine]:
    return list(
        db.execute(
            select(DocumentLine)
            .where(DocumentLine.document_id == document_id)
            .order_by(DocumentLine.position)
        ).scalars()
    )


def draft_json(document: Document, customer_name: str, lines: list[DocumentLine]) -> dict[str, Any]:
    """The draft representation (docs/07 §3.3): inputs plus amounts computed now."""
    result = engine.calculate_document([line_input(line) for line in lines])
    return {
        "id": str(document.id),
        "business_id": str(document.business_id),
        "doc_type": document.doc_type,
        "status": document.status,
        "tax_mode": document.tax_mode,
        "template_id": document.template_id,
        "currency": document.currency,
        "customer": {"id": str(document.customer_id), "display_name": customer_name},
        "number": None,
        "issue_date": None,
        "due_date": document.due_date.isoformat() if document.due_date else None,
        "reference": document.reference,
        "notes": document.notes,
        "terms": document.terms,
        "lines": [
            {
                "position": line.position,
                "description": line.description,
                "quantity": engine.quantity_str(line.quantity),
                "unit": line.unit,
                "unit_price": engine.money_str(line.unit_price),
                "discount_type": line.discount_type,
                "discount_value": (
                    engine.money_str(line.discount_value)
                    if line.discount_value is not None
                    else None
                ),
                "gross": engine.money_str(amounts.gross),
                "discount": engine.money_str(amounts.discount),
                "line_total": engine.money_str(amounts.line_total),
            }
            for line, amounts in zip(lines, result.lines, strict=True)
        ],
        "totals": totals_json(result.totals),
        "calc_version": engine.CALC_VERSION,
        "finalized_at": None,
        "snapshot_sha256": None,
        "pdf": None,
        "version": document.version,
        "seller": None,
        "buyer": None,
        "created_at": rfc3339(document.created_at),
        "updated_at": rfc3339(document.updated_at),
    }


def find_document(
    db: Session, org_id: uuid.UUID, document_id: uuid.UUID, *, lock: bool = False
) -> Document:
    """The organization's document by ID, or 404 (docs/04 §8)."""
    query = select(Document).where(Document.id == document_id, Document.org_id == org_id)
    if lock:
        query = query.with_for_update()
    document = db.execute(query).scalar_one_or_none()
    if document is None:
        raise AppError("not_found")
    return document


def customer_name(db: Session, document: Document) -> str:
    name = db.execute(
        select(Customer.display_name).where(Customer.id == document.customer_id)
    ).scalar_one()
    return str(name)


def _customer_in_business(
    db: Session, org_id: uuid.UUID, business_id: uuid.UUID, value: str
) -> uuid.UUID:
    try:
        customer_id = uuid.UUID(value)
        find_customer(db, org_id, business_id, customer_id)
    except (ValueError, AppError):
        raise field_problem(
            "/customer_id", "not_found", "Choose one of this business's customers."
        ) from None
    return customer_id


def _active_template(db: Session, template_id: str) -> str:
    template = find_template(db, template_id)
    if template is None or template.doc_type != "invoice":
        raise field_problem("/template_id", "not_found", "Choose an available template.")
    if not template.is_active:
        raise field_problem("/template_id", "inactive", "This template is no longer available.")
    return template.id


def _insert_lines(
    db: Session, document: Document, lines: Sequence[DocumentLineIn], now: datetime
) -> None:
    for position, line in enumerate(lines, start=1):
        db.add(
            DocumentLine(
                org_id=document.org_id,
                document_id=document.id,
                position=position,
                description=line.description,
                quantity=line.quantity,
                unit=line.unit,
                unit_price=line.unit_price,
                discount_type=line.discount_type,
                discount_value=line.discount_value,
                created_at=now,
            )
        )


def create_draft(
    db: Session,
    tenant: Tenant,
    business_id: uuid.UUID,
    *,
    now: datetime,
    fields: dict[str, Any],
) -> dict[str, Any]:
    lines: list[DocumentLineIn] = fields.get("lines", [])
    calculate([line.calc_input() for line in lines])
    with db.begin():
        find_business(db, tenant.org_id, business_id)
        customer_id = _customer_in_business(db, tenant.org_id, business_id, fields["customer_id"])
        template_id = _active_template(db, fields.get("template_id") or "classic@1")
        document = Document(
            org_id=tenant.org_id,
            business_id=business_id,
            customer_id=customer_id,
            doc_type="invoice",
            template_id=template_id,
            reference=fields.get("reference"),
            due_date=fields.get("due_date"),
            notes=fields.get("notes"),
            terms=fields.get("terms"),
            created_by=tenant.user_id,
            created_at=now,
            updated_at=now,
        )
        db.add(document)
        db.flush()
        _insert_lines(db, document, lines, now)
        db.flush()
        return draft_json(document, customer_name(db, document), draft_lines(db, document.id))


def get_draft_or_document(
    db: Session, org_id: uuid.UUID, document_id: uuid.UUID, *, now: datetime
) -> dict[str, Any]:
    with db.begin():
        document = find_document(db, org_id, document_id)
        return document_json(db, document, now)


def document_json(db: Session, document: Document, now: datetime) -> dict[str, Any]:
    """Draft: computed now. Finalised: built from the snapshot (docs/07 §3.3)."""
    if document.status == "draft":
        return draft_json(document, customer_name(db, document), draft_lines(db, document.id))
    from app.modules.documents.issued import finalized_json

    return finalized_json(db, document, now)


def update_draft(
    db: Session,
    tenant: Tenant,
    document_id: uuid.UUID,
    *,
    now: datetime,
    expected_version: int,
    changes: dict[str, Any],
) -> dict[str, Any]:
    lines: list[DocumentLineIn] | None = changes.get("lines")
    if lines is not None:
        calculate([line.calc_input() for line in lines])
    with db.begin():
        document = find_document(db, tenant.org_id, document_id, lock=True)
        if document.status != "draft":
            raise AppError("document_not_draft")
        check_version(expected_version, document.version)
        if "customer_id" in changes:
            document.customer_id = _customer_in_business(
                db, tenant.org_id, document.business_id, changes["customer_id"]
            )
        if "template_id" in changes:
            document.template_id = _active_template(db, changes["template_id"])
        for name in ("reference", "due_date", "notes", "terms"):
            if name in changes:
                setattr(document, name, changes[name])
        if lines is not None:
            db.execute(delete(DocumentLine).where(DocumentLine.document_id == document.id))
            _insert_lines(db, document, lines, now)
        document.version += 1
        document.updated_at = now
        db.flush()
        return draft_json(document, customer_name(db, document), draft_lines(db, document.id))


def delete_draft(
    db: Session, tenant: Tenant, document_id: uuid.UUID, *, expected_version: int
) -> None:
    with db.begin():
        document = find_document(db, tenant.org_id, document_id, lock=True)
        if document.status != "draft":
            raise AppError("document_not_draft")
        check_version(expected_version, document.version)
        db.delete(document)
