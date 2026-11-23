"""Final PDFs: post-commit render → private S3 → ``stored_files`` → artifact ``ready``
(docs/04 §11, §12; docs/09 §11; E-22, E-23).

The render uses only the frozen snapshot; the worker re-checks its canonical hash. An
artifact becomes ``ready`` together with its ``stored_files`` row in one transaction. A
failed render or storage error leaves the document finalised with the artifact ``failed``;
a retry renders the same snapshot again and never renumbers.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from importlib.metadata import version as package_version
from typing import Any

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.audit.service import record_event
from app.modules.documents import drafts
from app.modules.documents.issued import RETRY_AFTER_PENDING, load_artifact, pdf_json
from app.modules.documents.models import DocumentArtifact, DocumentSnapshot
from app.modules.rendering import registry
from app.modules.rendering.pool import RenderError, RenderJob
from app.modules.storage.models import StoredFile
from app.modules.storage.objects import (
    ObjectMissingError,
    StorageUnavailableError,
    final_pdf_key,
    get_object,
    put_pdf,
)
from app.modules.tenancy.dependencies import Tenant

logger = logging.getLogger("app.documents")

RENDER_ERROR_CODES = {"render_error", "render_timeout", "snapshot_integrity"}


def renderer_version() -> str:
    return f"weasyprint {package_version('weasyprint')}"


def start_first_render(state: Any, artifact_id: uuid.UUID) -> None:
    """Background task after finalisation: claim attempt 1, then render and store."""
    now = state.clock.now()
    with state.db_sessions() as db, db.begin():
        attempt = db.execute(
            update(DocumentArtifact)
            .where(
                DocumentArtifact.id == artifact_id,
                DocumentArtifact.status == "pending",
                DocumentArtifact.attempts == 0,
            )
            .values(attempts=DocumentArtifact.attempts + 1, updated_at=now)
            .returning(DocumentArtifact.attempts)
        ).scalar_one_or_none()
    if attempt is not None:
        render_attempt(state, artifact_id, int(attempt))


def render_attempt(state: Any, artifact_id: uuid.UUID, attempt: int) -> None:
    """Render the snapshot, store the PDF privately, record the outcome. Never raises."""
    try:
        _render_attempt(state, artifact_id, attempt)
    except Exception:
        logger.exception("final PDF render crashed")
        _record_failure(state, artifact_id, "render_error", attempt)


def _render_attempt(state: Any, artifact_id: uuid.UUID, attempt: int) -> None:
    with state.db_sessions() as db, db.begin():
        artifact = db.get(DocumentArtifact, artifact_id)
        if artifact is None or artifact.status != "pending":
            return
        snapshot = db.execute(
            select(DocumentSnapshot).where(DocumentSnapshot.document_id == artifact.document_id)
        ).scalar_one()
        job = RenderJob(
            template_id=artifact.template_id,
            payload=snapshot.payload,
            preview=False,
            expected_sha256=snapshot.canonical_sha256,
        )
        org_id, document_id = artifact.org_id, artifact.document_id
    try:
        pdf = state.render_pool.render(job)
    except RenderError as error:
        code = error.code if error.code in RENDER_ERROR_CODES else "render_error"
        logger.error("final PDF render failed: %s", code)
        _record_failure(state, artifact_id, code, attempt)
        return

    digest = hashlib.sha256(pdf).hexdigest()
    key = final_pdf_key(org_id, document_id, artifact_id)
    bucket = state.settings.s3_bucket
    try:
        stored = put_pdf(state.s3, bucket, key, pdf)
    except StorageUnavailableError:
        _record_failure(state, artifact_id, "storage_error", attempt)
        return

    now = state.clock.now()
    template = registry.get(job.template_id)
    with state.db_sessions() as db, db.begin():
        stored_file = StoredFile(
            org_id=org_id,
            purpose="document_pdf",
            bucket=bucket,
            object_key=key,
            content_type="application/pdf",
            size_bytes=len(pdf),
            sha256=digest,
            object_version_id=stored.version_id,
            created_at=now,
        )
        db.add(stored_file)
        db.flush()
        updated = db.execute(
            update(DocumentArtifact)
            .where(DocumentArtifact.id == artifact_id, DocumentArtifact.status == "pending")
            .values(
                status="ready",
                stored_file_id=stored_file.id,
                rendered_at=now,
                template_sha256=template.sha256,
                renderer_version=renderer_version(),
                last_error_code=None,
                updated_at=now,
            )
            .returning(DocumentArtifact.id)
        ).scalar_one_or_none()
        if updated is None:  # another attempt finished first; keep the ready one
            db.rollback()
            return
        record_event(
            db,
            "document.pdf_rendered",
            occurred_at=now,
            org_id=org_id,
            subject_type="document",
            subject_id=document_id,
            details={
                "artifact_id": str(artifact_id),
                "sha256": digest,
                "size_bytes": len(pdf),
                "attempt": attempt,
            },
        )


def _record_failure(state: Any, artifact_id: uuid.UUID, code: str, attempt: int) -> None:
    now = state.clock.now()
    with state.db_sessions() as db, db.begin():
        row = db.execute(
            update(DocumentArtifact)
            .where(DocumentArtifact.id == artifact_id, DocumentArtifact.status == "pending")
            .values(status="failed", last_error_code=code, updated_at=now)
            .returning(DocumentArtifact.org_id, DocumentArtifact.document_id)
        ).first()
        if row is None:
            return
        record_event(
            db,
            "document.pdf_render_failed",
            occurred_at=now,
            org_id=row.org_id,
            subject_type="document",
            subject_id=row.document_id,
            details={"artifact_id": str(artifact_id), "error_code": code, "attempt": attempt},
        )


@dataclass(frozen=True)
class RetryOutcome:
    status: int
    pdf: dict[str, Any]
    artifact_id: uuid.UUID | None
    attempt: int | None


def claim_retry(
    db: Session, tenant: Tenant, document_id: uuid.UUID, *, now: datetime, limiter: Any
) -> RetryOutcome:
    """E-23: claim the artifact atomically; the render is scheduled by the caller."""
    with db.begin():
        document = drafts.find_document(db, tenant.org_id, document_id)
        if document.status != "finalized":
            raise AppError("document_not_finalized")
        limiter.check(str(document.id), now)
        artifact, stored = load_artifact(db, document.id)
        if artifact.status == "ready":
            return RetryOutcome(200, pdf_json(artifact, stored, now), None, None)
        claimed = db.execute(
            update(DocumentArtifact)
            .where(
                DocumentArtifact.id == artifact.id,
                or_(
                    DocumentArtifact.status == "failed",
                    and_(
                        DocumentArtifact.status == "pending",
                        DocumentArtifact.updated_at < now - RETRY_AFTER_PENDING,
                    ),
                ),
            )
            .values(status="pending", attempts=DocumentArtifact.attempts + 1, updated_at=now)
            .returning(DocumentArtifact.attempts)
        ).scalar_one_or_none()
        if claimed is None:
            raise AppError("pdf_render_in_progress")
        db.refresh(artifact)
        return RetryOutcome(202, pdf_json(artifact, None, now), artifact.id, int(claimed))


@dataclass(frozen=True)
class Download:
    data: bytes
    filename: str
    sha256: str


def download(
    db: Session, state: Any, tenant: Tenant, document_id: uuid.UUID, *, record: bool
) -> Download:
    """E-22: the stored bytes, served only if their SHA-256 equals the recorded value."""
    with db.begin():
        document = drafts.find_document(db, tenant.org_id, document_id)
        if document.status != "finalized":
            raise AppError("document_not_finalized")
        artifact, stored = load_artifact(db, document.id)
        if artifact.status != "ready" or stored is None:
            raise AppError("pdf_not_ready", extra={"pdf_status": artifact.status})
        number = str(document.document_number)
        bucket, key, expected = stored.bucket, stored.object_key, stored.sha256
        artifact_id = artifact.id
    try:
        data = get_object(state.s3, bucket, key)
    except ObjectMissingError:
        logger.error("integrity check failed: stored PDF missing", extra={"event": "integrity"})
        raise AppError("integrity_check_failed") from None
    except StorageUnavailableError:
        raise AppError("dependency_unavailable") from None
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected:
        logger.error(
            "integrity check failed: stored PDF hash differs", extra={"event": "integrity"}
        )
        raise AppError("integrity_check_failed")
    if record:
        with db.begin():
            record_event(
                db,
                "document.pdf_downloaded",
                occurred_at=state.clock.now(),
                org_id=tenant.org_id,
                actor_user_id=tenant.user_id,
                subject_type="document",
                subject_id=document_id,
                details={"artifact_id": str(artifact_id), "sha256": digest},
            )
    return Download(data=data, filename=number.replace("/", "-") + ".pdf", sha256=digest)


def content_digest(hex_digest: str) -> str:
    """RFC 9530 ``Content-Digest`` value: ``sha-256=:<base64>:``."""
    return f"sha-256=:{base64.b64encode(bytes.fromhex(hex_digest)).decode()}:"
