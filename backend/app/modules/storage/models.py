"""ORM mapping for ``stored_files`` (docs/06 §3.13). Rows are only ever inserted."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class StoredFile(Base):
    __tablename__ = "stored_files"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID]
    purpose: Mapped[str] = mapped_column(Text, server_default=text("'document_pdf'"))
    bucket: Mapped[str] = mapped_column(Text)
    object_key: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(Text, server_default=text("'application/pdf'"))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(Text)
    object_version_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
