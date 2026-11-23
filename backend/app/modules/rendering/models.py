"""ORM mapping for ``templates``, the global template catalogue (docs/06 §3.7)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    code: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer)
    doc_type: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    tier: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
