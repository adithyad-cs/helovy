"""HTTP helpers: ETag / If-Match (docs/07 §1.6) and opaque, signed list cursors (§1.8)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime

from fastapi import Request

from app.core.errors import AppError

_IF_MATCH = re.compile(r'^"([1-9][0-9]{0,8})"$')


def etag(version: int) -> str:
    """A strong ETag for a row version, for example ``"4"``."""
    return f'"{version}"'


def require_if_match(request: Request) -> int:
    """The version in ``If-Match``: missing → 428; not a strong version ETag → 400."""
    value = request.headers.get("if-match")
    if value is None:
        raise AppError("precondition_required")
    match = _IF_MATCH.match(value.strip())
    if match is None:
        raise AppError("malformed_request", detail='Send If-Match as the ETag, for example "4".')
    return int(match.group(1))


def check_version(expected: int, current: int) -> None:
    if expected != current:
        raise AppError("version_mismatch")


def invalid_cursor() -> AppError:
    return AppError(
        "validation_failed",
        detail="1 field needs attention.",
        errors=[
            {
                "pointer": "/cursor",
                "code": "invalid_format",
                "message": "This page link is no longer valid. Start again from the first page.",
            }
        ],
    )


@dataclass(frozen=True)
class Cursor:
    created_at: datetime
    id: uuid.UUID


def _signature(key: bytes, scope: str, payload: str) -> str:
    digest = hmac.new(key, f"cursor:{scope}:{payload}".encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest[:16]).rstrip(b"=").decode()


def encode_cursor(key: bytes, scope: str, created_at: datetime, row_id: uuid.UUID) -> str:
    """Opaque cursor: base64url of {t, id, sig}; the signature binds it to its list (scope)."""
    payload = f"{created_at.isoformat()}|{row_id}"
    body = {"t": created_at.isoformat(), "id": str(row_id), "sig": _signature(key, scope, payload)}
    raw = json.dumps(body, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def decode_cursor(key: bytes, scope: str, cursor: str) -> Cursor:
    """The position, or 422 ``validation_failed`` at ``/cursor`` when tampered or foreign."""
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        body = json.loads(raw)
        created_at = datetime.fromisoformat(body["t"])
        row_id = uuid.UUID(body["id"])
        signature = str(body["sig"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise invalid_cursor() from None
    if created_at.tzinfo is None:
        raise invalid_cursor()
    expected = _signature(key, scope, f"{created_at.isoformat()}|{row_id}")
    if not hmac.compare_digest(expected, signature):
        raise invalid_cursor()
    return Cursor(created_at, row_id)
