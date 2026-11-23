"""Structured JSON logging with the request ID on every line (docs/04 §5, docs/12 §10).

Never log passwords, cookies, tokens, CSRF tokens, idempotency keys, request bodies,
emails, addresses, phone numbers, line contents or PDF bytes. Access lines carry the
matched route template (for example ``/api/v1/documents/{document_id}``), never the raw
path or query string.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Extra attributes copied from a LogRecord into the JSON line when present.
_EXTRA_FIELDS = ("event", "method", "route", "status", "duration_ms", "org_id", "user_id")
_HANDLER_MARK = "_hive_docs_json_handler"


class JsonFormatter(logging.Formatter):
    """One JSON object per line: ts, level, logger, msg, request_id and known extras."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or request_id_var.get(),
        }
        for field in _EXTRA_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str) -> None:
    """Install the JSON handler on the root logger once; route uvicorn's loggers through it.

    Existing handlers (for example pytest's log capture) are left in place.
    """
    root = logging.getLogger()
    root.setLevel(level)
    if not any(getattr(handler, _HANDLER_MARK, False) for handler in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        setattr(handler, _HANDLER_MARK, True)
        root.addHandler(handler)
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    # The application writes its own access line (route template, no query string).
    logging.getLogger("uvicorn.access").disabled = True
