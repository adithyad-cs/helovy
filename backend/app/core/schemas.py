"""Request-schema building blocks (docs/04 §5; docs/07 §1.4-§1.5; docs/09 §4.2; docs/12 §6).

- ``StrictModel``: Pydantic v2 strict mode, unknown fields rejected (``unknown_field``).
- Text normalisation: trim, CRLF → LF, U+0000 and other C0 controls rejected (TAB and LF
  allowed only in multi-line fields), empty optional text → ``null``; lengths in code points.
- ``require_json_body``: a request body must be sent as ``application/json`` (400
  ``malformed_request`` otherwise).
- Validators raise ``PydanticCustomError`` whose type *is* the documented field error code,
  so the problem handler can pass it through unchanged.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from fastapi import Request
from pydantic import BaseModel, ConfigDict
from pydantic_core import PydanticCustomError

from app.core.errors import DOCUMENTED_FIELD_CODES, AppError

FIELD_ERROR_CODES = DOCUMENTED_FIELD_CODES  # docs/07 §1.5

BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})

_SINGLE_LINE_FORBIDDEN = re.compile(r"[\x00-\x1f\x7f]")
_MULTI_LINE_FORBIDDEN = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


def field_error(code: str, message: str) -> PydanticCustomError:
    if code not in FIELD_ERROR_CODES:
        raise ValueError(f"unknown field error code {code!r}")
    return PydanticCustomError(code, message)


def clean_text(
    value: str,
    *,
    max_length: int,
    multiline: bool = False,
    required: bool = False,
    min_length: int = 1,
) -> str | None:
    """Normalise one text field per docs/09 §4.2; raise a field error when it is invalid."""
    text = value.replace("\r\n", "\n").strip()
    forbidden = _MULTI_LINE_FORBIDDEN if multiline else _SINGLE_LINE_FORBIDDEN
    if forbidden.search(text):
        raise field_error("invalid_format", "Remove control characters and line breaks.")
    if not text:
        if required:
            raise field_error("required", "This field is required.")
        return None
    if len(text) < min_length:
        raise field_error("too_short", f"Use at least {min_length} characters.")
    if len(text) > max_length:
        raise field_error("too_long", f"Use at most {max_length:,} characters.")
    return text


def require_json_body(request: Request) -> None:
    """Router dependency: a body must be ``application/json`` (docs/07 §1.1)."""
    if request.method not in BODY_METHODS:
        return
    length = request.headers.get("content-length")
    chunked = "chunked" in request.headers.get("transfer-encoding", "").lower()
    if not chunked and (length is None or length == "0"):
        return  # no body
    media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type != "application/json":
        raise AppError("malformed_request", detail="Send the request body as application/json.")


def rfc3339(moment: datetime) -> str:
    """RFC 3339 in UTC with seconds precision, for example 2026-11-25T05:42:10Z (docs/07 §1.4)."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
