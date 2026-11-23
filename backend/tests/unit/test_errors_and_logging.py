"""Problem-details helpers and the JSON log format (docs/07 §1.5, docs/12 §10)."""

from __future__ import annotations

import json
import logging

import pytest

from app.core.errors import CATALOGUE, AppError, json_pointer
from app.core.logging import JsonFormatter, request_id_var


def test_catalogue_has_the_25_documented_codes() -> None:
    # docs/07 §1.12 (documentation 1.2): 24 codes plus method_not_allowed.
    assert len(CATALOGUE) == 25
    assert CATALOGUE["not_found"].status == 404
    assert CATALOGUE["method_not_allowed"].status == 405
    assert CATALOGUE["payload_too_large"].status == 413
    assert CATALOGUE["validation_failed"].status == 422
    assert CATALOGUE["dependency_unavailable"].status == 503


def test_unknown_error_code_is_a_programming_error() -> None:
    with pytest.raises(ValueError, match="unknown error code"):
        AppError("teapot")


@pytest.mark.parametrize(
    ("loc", "pointer"),
    [
        (("body", "lines", 1, "discount_value"), "/lines/1/discount_value"),
        (("body", "lines", 0, "quantity"), "/lines/0/quantity"),
        (("query", "cursor"), "/cursor"),
        (("body", "a/b", "c~d"), "/a~1b/c~0d"),
        (("body",), ""),
    ],
)
def test_json_pointer(loc: tuple[int | str, ...], pointer: str) -> None:
    assert json_pointer(loc) == pointer


def _record(msg: str, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord("app.test", logging.INFO, __file__, 1, msg, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_emits_one_json_object_with_request_id() -> None:
    token = request_id_var.set("req_test_123")
    try:
        line = JsonFormatter().format(
            _record("request", route="/healthz", status=200, duration_ms=1.5, method="GET")
        )
    finally:
        request_id_var.reset(token)
    payload = json.loads(line)
    assert "\n" not in line
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["msg"] == "request"
    assert payload["request_id"] == "req_test_123"
    assert payload["route"] == "/healthz"
    assert payload["status"] == 200
    assert payload["ts"].endswith("Z")


def test_json_formatter_includes_tracebacks_server_side() -> None:
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        import sys

        record = _record("failure")
        record.exc_info = sys.exc_info()
    payload = json.loads(JsonFormatter().format(record))
    assert "RuntimeError: boom" in payload["exc"]
