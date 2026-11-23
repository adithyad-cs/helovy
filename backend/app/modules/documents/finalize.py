"""Atomic finalisation, exactly as docs/09 §8 (E-21; docs/04 §10).

One READ COMMITTED transaction with ``lock_timeout`` 5 s; lock order idempotency record →
document → number series. The number is allocated here and nowhere else, formatted in
Python. The snapshot, the finalised document, the pending artifact, the audit event and the
completed idempotency record commit together; the PDF is rendered after commit.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import psycopg.errors
from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.errors import AppError
from app.core.schemas import rfc3339
from app.core.validation import state_name
from app.modules.audit.service import record_event
from app.modules.businesses.models import Business
from app.modules.calc import engine
from app.modules.calc.engine import CalcError
from app.modules.customers.models import Customer
from app.modules.documents import drafts, numbering
from app.modules.documents.issued import body_from_snapshot, pdf_json
from app.modules.documents.models import (
    Document,
    DocumentArtifact,
    DocumentSnapshot,
    IdempotencyKey,
    NumberSeries,
)
from app.modules.documents.snapshot import SCHEMA_VERSION, TAX_RULE_SET, build_payload
from app.modules.documents.snapshot import canonical_sha256 as snapshot_hash
from app.modules.rendering.catalogue import find_template
from app.modules.tenancy.dependencies import Tenant

SCOPE = "document.finalize"
KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
KEY_LIFETIME = timedelta(hours=24)


@dataclass(frozen=True)
class FinalizeOutcome:
    status: int
    body: dict[str, Any]
    replayed: bool
    artifact_id: uuid.UUID | None


def check_idempotency_key(value: str | None) -> str:
    """Step 0: present (400 ``idempotency_key_missing``) and well formed (400)."""
    if value is None:
        raise AppError("idempotency_key_missing")
    if not KEY_PATTERN.match(value):
        raise AppError(
            "malformed_request",
            detail="Idempotency-Key must be 8-128 characters of A-Z a-z 0-9 _ -.",
        )
    return value


def fingerprint(document_id: uuid.UUID, if_match: str) -> str:
    """SHA-256 hex of ``"POST\\n/api/v1/documents/{id}/finalize\\n{If-Match}"`` (09 §8)."""
    message = f"POST\n/api/v1/documents/{document_id}/finalize\n{if_match}"
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def _lock_timeout(error: OperationalError) -> bool:
    return isinstance(error.orig, psycopg.errors.LockNotAvailable)


def _blocked(errors: list[dict[str, str]]) -> AppError:
    return AppError(
        "finalization_blocked",
        detail="This invoice can't be finalised yet.",
        errors=errors,
    )


def _preconditions(
    db: Session, document: Document, lines: list[Any], issue: Any
) -> engine.DocumentResult:
    """Step 5 (and step 6: the recalculation); 422 ``finalization_blocked`` with reasons."""
    errors: list[dict[str, str]] = []
    result: engine.DocumentResult | None = None
    if not lines:
        errors.append(
            {"pointer": "/lines", "code": "no_lines", "message": "Add at least one line."}
        )
    elif len(lines) > engine.MAX_LINES:
        errors.append(
            {"pointer": "/lines", "code": "too_many_lines", "message": "Use at most 200 lines."}
        )
    else:
        try:
            result = engine.calculate_document([drafts.line_input(line) for line in lines])
        except CalcError as error:
            errors.append({"pointer": "/lines", "code": error.code, "message": error.message})
        if result is not None and result.totals.grand_total <= engine.ZERO:
            errors.append({"pointer": "/lines", "code": "zero_total",
                           "message": "The total must be more than ₹0.00."})  # fmt: skip
    if document.due_date is not None and document.due_date < issue:
        errors.append({"pointer": "/due_date", "code": "due_date_before_issue_date",
                       "message": "The due date is before today's date."})  # fmt: skip
    template = find_template(db, document.template_id)
    if template is None or not template.is_active:
        errors.append({"pointer": "/template_id", "code": "inactive",
                       "message": "The selected template is no longer available."})  # fmt: skip
    if errors or result is None:
        raise _blocked(errors)
    return result


def finalize(
    db: Session,
    tenant: Tenant,
    clock: Clock,
    document_id: uuid.UUID,
    *,
    idem_key: str,
    if_match: str,
    expected_version: int,
) -> FinalizeOutcome:
    request_fingerprint = fingerprint(document_id, if_match)
    try:
        with db.begin():
            # Step 1.
            db.execute(text("SET LOCAL lock_timeout = '5s'"))
            started = clock.now()
            # Step 2: the idempotency record (first lock).
            try:
                inserted = db.execute(
                    pg_insert(IdempotencyKey)
                    .values(
                        org_id=tenant.org_id,
                        scope=SCOPE,
                        idem_key=idem_key,
                        request_fingerprint=request_fingerprint,
                        status="in_progress",
                        user_id=tenant.user_id,
                        created_at=started,
                        expires_at=started + KEY_LIFETIME,
                    )
                    .on_conflict_do_nothing()
                    .returning(IdempotencyKey.idem_key)
                ).first()
            except OperationalError as error:
                if _lock_timeout(error):
                    raise AppError("idempotency_in_progress") from None
                raise
            if inserted is None:
                existing = db.execute(
                    select(IdempotencyKey).where(
                        IdempotencyKey.org_id == tenant.org_id,
                        IdempotencyKey.scope == SCOPE,
                        IdempotencyKey.idem_key == idem_key,
                    )
                ).scalar_one()
                if existing.request_fingerprint != request_fingerprint:
                    raise AppError("idempotency_key_mismatch")
                if existing.status != "completed" or existing.response_body is None:
                    raise AppError("idempotency_in_progress")
                return FinalizeOutcome(
                    status=int(existing.response_status or 200),
                    body=dict(existing.response_body),
                    replayed=True,
                    artifact_id=None,
                )

            # Step 3: the document (second lock).
            try:
                document = drafts.find_document(db, tenant.org_id, document_id, lock=True)
            except OperationalError as error:
                if _lock_timeout(error):
                    raise AppError("dependency_unavailable") from None
                raise
            if document.status != "draft":
                raise AppError("document_not_draft")
            if document.version != expected_version:
                raise AppError("version_mismatch")

            # Step 4: one instant for finalized_at and the issue date.
            finalized_at = clock.transaction_now(db)
            issue = numbering.issue_date_for(finalized_at)
            fy = numbering.financial_year(issue)

            # Steps 5 and 6.
            lines = drafts.draft_lines(db, document.id)
            result = _preconditions(db, document, lines, issue)

            # Step 7: the number series (third lock).
            db.execute(
                pg_insert(NumberSeries)
                .values(
                    org_id=tenant.org_id,
                    business_id=document.business_id,
                    doc_type="invoice",
                    financial_year=fy,
                    prefix=numbering.PREFIX,
                    next_seq=1,
                    created_at=finalized_at,
                    updated_at=finalized_at,
                )
                .on_conflict_do_nothing(
                    index_elements=["business_id", "doc_type", "financial_year"]
                )
            )
            try:
                series_id, prefix, sequence = db.execute(
                    update(NumberSeries)
                    .where(
                        NumberSeries.business_id == document.business_id,
                        NumberSeries.doc_type == "invoice",
                        NumberSeries.financial_year == fy,
                    )
                    .values(next_seq=NumberSeries.next_seq + 1, updated_at=finalized_at)
                    .returning(NumberSeries.id, NumberSeries.prefix, NumberSeries.next_seq - 1)
                ).one()
            except IntegrityError:
                raise AppError("number_series_exhausted") from None
            except OperationalError as error:
                if _lock_timeout(error):
                    raise AppError("dependency_unavailable") from None
                raise
            try:
                number = numbering.format_number(str(prefix), fy, int(sequence))
            except numbering.NumberSeriesExhaustedError:
                raise AppError("number_series_exhausted") from None

            # Step 8: the immutable snapshot.
            business = db.get(Business, document.business_id)
            customer = db.get(Customer, document.customer_id)
            if business is None or customer is None:  # guarded by composite foreign keys
                raise AppError("internal_error")
            payload = build_payload(
                document=document,
                business=business,
                business_state_name=state_name(business.state_code),
                customer=customer,
                customer_state_name=state_name(customer.state_code),
                lines=lines,
                result=result,
                number=number,
                financial_year=fy,
                issue_date=issue.isoformat(),
                finalized_at=rfc3339(finalized_at),
            )
            snapshot = DocumentSnapshot(
                org_id=tenant.org_id,
                document_id=document.id,
                schema_version=SCHEMA_VERSION,
                calc_version=engine.CALC_VERSION,
                tax_rule_set=TAX_RULE_SET,
                template_id=document.template_id,
                payload=payload,
                canonical_sha256=snapshot_hash(payload),
                created_at=finalized_at,
            )
            db.add(snapshot)
            db.flush()

            # Step 9: the document becomes finalised.
            document.status = "finalized"
            document.number_series_id = series_id
            document.sequence_no = int(sequence)
            document.document_number = number
            document.issue_date = issue
            document.finalized_at = finalized_at
            document.finalized_by = tenant.user_id
            document.version += 1
            document.updated_at = finalized_at
            db.flush()

            # Step 10: the pending artifact.
            artifact = DocumentArtifact(
                org_id=tenant.org_id,
                document_id=document.id,
                kind="final_pdf",
                status="pending",
                attempts=0,
                template_id=document.template_id,
                created_at=finalized_at,
                updated_at=finalized_at,
            )
            db.add(artifact)
            db.flush()

            # Step 11: the audit event.
            record_event(
                db,
                "document.finalized",
                occurred_at=finalized_at,
                org_id=tenant.org_id,
                actor_user_id=tenant.user_id,
                subject_type="document",
                subject_id=document.id,
                details={"number": number, "snapshot_sha256": snapshot.canonical_sha256},
            )

            # Step 12: the stored response.
            body = body_from_snapshot(document, snapshot, pdf_json(artifact, None, finalized_at))
            db.execute(
                update(IdempotencyKey)
                .where(
                    IdempotencyKey.org_id == tenant.org_id,
                    IdempotencyKey.scope == SCOPE,
                    IdempotencyKey.idem_key == idem_key,
                )
                .values(
                    status="completed",
                    response_status=200,
                    response_body=body,
                    resource_id=document.id,
                )
            )
            artifact_id = artifact.id
        # Step 13: committed.
    except OperationalError as error:
        if _lock_timeout(error):
            raise AppError("dependency_unavailable") from None
        raise
    return FinalizeOutcome(status=200, body=body, replayed=False, artifact_id=artifact_id)
