"""HTML and PDF rendering of a snapshot or preview payload (docs/04 §11; docs/09 §13).

Runs inside a render worker process. Templates load only from their registered directory,
whose files must hash to the registered value; Jinja2 uses autoescape and StrictUndefined;
WeasyPrint gets the restricted fetcher, no presentational hints and no attachments.
"""

from __future__ import annotations

from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.modules.rendering import constants, registry
from app.modules.rendering.fetcher import ASSETS_DIR, RestrictedFetcher
from app.modules.rendering.formatting import FILTERS


class TemplateIntegrityError(RuntimeError):
    """The template files do not match the registered SHA-256."""


def environment(template_id: str) -> Environment:
    entry = registry.get(template_id)
    env = Environment(
        loader=FileSystemLoader(entry.directory),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(FILTERS)
    return env


def render_html(template_id: str, payload: dict[str, Any], *, preview: bool) -> str:
    """The template's HTML for a payload (also used by template-level test assertions)."""
    if not registry.matches(template_id):
        raise TemplateIntegrityError(template_id)
    context = {
        "doc": payload["document"],
        "seller": payload["seller"],
        "buyer": payload["buyer"],
        "lines": payload["lines"],
        "totals": payload["totals"],
        "specimen_text": payload["labels"]["specimen_text"],
        "preview": preview,
        "watermark_text": constants.WATERMARK_TEXT,
        "preview_number": constants.PREVIEW_NUMBER,
        "preview_date": constants.PREVIEW_DATE,
        "title": constants.DOCUMENT_TITLE,
    }
    return environment(template_id).get_template("template.html").render(context)


def render_pdf(template_id: str, payload: dict[str, Any], *, preview: bool) -> bytes:
    import weasyprint  # imported in the worker only: the API process never renders

    html = render_html(template_id, payload, preview=preview)
    document = weasyprint.HTML(
        string=html, base_url=ASSETS_DIR.as_uri() + "/", url_fetcher=RestrictedFetcher()
    )
    pdf: bytes = document.write_pdf(presentational_hints=False, attachments=None)
    return pdf


def renderer_version() -> str:
    import weasyprint

    return f"weasyprint {weasyprint.__version__}"
