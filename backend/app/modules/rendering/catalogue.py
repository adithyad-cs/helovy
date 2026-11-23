"""The template catalogue (docs/07 E-13): read-only, global, not tenant-owned."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.rendering.models import Template


def template_json(template: Template) -> dict[str, Any]:
    return {
        "id": template.id,
        "code": template.code,
        "version": template.version,
        "name": template.name,
        "description": template.description,
        "tier": template.tier,
        "doc_type": template.doc_type,
    }


def list_active(db: Session, doc_type: str) -> list[Template]:
    with db.begin():
        return list(
            db.execute(
                select(Template)
                .where(Template.doc_type == doc_type, Template.is_active.is_(True))
                .order_by(Template.code, Template.version)
            ).scalars()
        )


def find_template(db: Session, template_id: str) -> Template | None:
    """Inside the caller's transaction: the template row, active or not."""
    return db.get(Template, template_id)
