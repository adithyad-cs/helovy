"""Finalised documents: the representation built from the snapshot (docs/07 §3.3) and the
PDF status block. Everything comes from the snapshot except ``pdf`` and ``version``."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.schemas import rfc3339
from app.modules.documents.models import Document, DocumentArtifact, DocumentSnapshot
from app.modules.storage.models import StoredFile

RETRY_AFTER_PENDING = timedelta(seconds=120)


def pdf_json(
    artifact: DocumentArtifact, stored: StoredFile | None, now: datetime
) -> dict[str, Any]:
    ready = artifact.status == "ready" and stored is not None
    stale = artifact.status == "pending" and artifact.updated_at < now - RETRY_AFTER_PENDING
    return {
        "status": artifact.status,
        "sha256": stored.sha256 if ready and stored else None,
        "size_bytes": stored.size_bytes if ready and stored else None,
        "rendered_at": rfc3339(artifact.rendered_at) if artifact.rendered_at else None,
        "attempts": artifact.attempts,
        "last_error_code": artifact.last_error_code,
        "retry_available": artifact.status == "failed" or stale,
    }


def load_artifact(
    db: Session, document_id: uuid.UUID
) -> tuple[DocumentArtifact, StoredFile | None]:
    artifact = db.execute(
        select(DocumentArtifact).where(
            DocumentArtifact.document_id == document_id, DocumentArtifact.kind == "final_pdf"
        )
    ).scalar_one()
    stored = db.get(StoredFile, artifact.stored_file_id) if artifact.stored_file_id else None
    return artifact, stored


def body_from_snapshot(
    document: Document, snapshot: DocumentSnapshot, pdf: dict[str, Any]
) -> dict[str, Any]:
    payload = snapshot.payload
    doc = payload["document"]
    return {
        "id": str(document.id),
        "business_id": str(document.business_id),
        "doc_type": doc["doc_type"],
        "status": "finalized",
        "tax_mode": document.tax_mode,
        "template_id": doc["template_id"],
        "currency": doc["currency"],
        "customer": {
            "id": payload["buyer"]["customer_id"],
            "display_name": payload["buyer"]["display_name"],
        },
        "number": doc["number"],
        "issue_date": doc["issue_date"],
        "due_date": doc["due_date"],
        "reference": doc["reference"],
        "notes": doc["notes"],
        "terms": doc["terms"],
        "lines": payload["lines"],
        "totals": payload["totals"],
        "calc_version": payload["calc_version"],
        "finalized_at": doc["finalized_at"],
        "snapshot_sha256": snapshot.canonical_sha256,
        "pdf": pdf,
        "version": document.version,
        "created_at": rfc3339(document.created_at),
        "updated_at": rfc3339(document.updated_at),
        # The issued seller and buyer blocks, for the read-only details page (docs/08 §19).
        "seller": payload["seller"],
        "buyer": payload["buyer"],
    }


def finalized_json(db: Session, document: Document, now: datetime) -> dict[str, Any]:
    snapshot = db.execute(
        select(DocumentSnapshot).where(DocumentSnapshot.document_id == document.id)
    ).scalar_one()
    artifact, stored = load_artifact(db, document.id)
    return body_from_snapshot(document, snapshot, pdf_json(artifact, stored, now))
