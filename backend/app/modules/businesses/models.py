"""ORM mapping for ``businesses`` (docs/06 §3.5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID]
    legal_name: Mapped[str] = mapped_column(Text)
    trade_name: Mapped[str | None] = mapped_column(Text)
    address_line1: Mapped[str] = mapped_column(Text)
    address_line2: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str] = mapped_column(Text)
    state_code: Mapped[str] = mapped_column(Text)
    postal_code: Mapped[str] = mapped_column(Text)
    country_code: Mapped[str] = mapped_column(Text, server_default=text("'IN'"))
    phone: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    gstin: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
