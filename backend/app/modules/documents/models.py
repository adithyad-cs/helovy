"""ORM mappings for ``documents``, ``document_lines`` and ``number_series`` (docs/06 §3.8-§3.10)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, SmallInteger, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID]
    business_id: Mapped[uuid.UUID]
    customer_id: Mapped[uuid.UUID]
    doc_type: Mapped[str] = mapped_column(Text, server_default=text("'invoice'"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'draft'"))
    tax_mode: Mapped[str] = mapped_column(Text, server_default=text("'no_tax'"))
    template_id: Mapped[str] = mapped_column(Text, server_default=text("'classic@1'"))
    currency: Mapped[str] = mapped_column(Text, server_default=text("'INR'"))
    reference: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    terms: Mapped[str | None] = mapped_column(Text)
    number_series_id: Mapped[uuid.UUID | None]
    sequence_no: Mapped[int | None] = mapped_column(Integer)
    document_number: Mapped[str | None] = mapped_column(Text)
    issue_date: Mapped[date | None] = mapped_column(Date)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finalized_by: Mapped[uuid.UUID | None]
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    created_by: Mapped[uuid.UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DocumentLine(Base):
    """Draft inputs only; computed amounts are never stored (docs/09 §9)."""

    __tablename__ = "document_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID]
    document_id: Mapped[uuid.UUID]
    position: Mapped[int] = mapped_column(SmallInteger)
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit: Mapped[str | None] = mapped_column(Text)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    discount_type: Mapped[str] = mapped_column(Text, server_default=text("'none'"))
    discount_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class NumberSeries(Base):
    __tablename__ = "number_series"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID]
    business_id: Mapped[uuid.UUID]
    doc_type: Mapped[str] = mapped_column(Text)
    financial_year: Mapped[str] = mapped_column(Text)
    prefix: Mapped[str] = mapped_column(Text)
    next_seq: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
