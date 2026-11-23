"""UT-SEC-01 (Argon2id) and UT-SEC-02 (CSRF token) — docs/11 §2.1; docs/12 §3, §4.2."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import uuid
from unittest import mock

from app.modules.auth import security

KEY = secrets.token_bytes(32)
_PARAMS = re.compile(r"^\$argon2id\$v=19\$m=(\d+),t=(\d+),p=(\d+)\$")


def test_ut_sec_01_argon2id_hash_verify_and_parameters() -> None:
    password = secrets.token_urlsafe(16)
    hashed = security.hash_password(password)
    assert hashed.startswith("$argon2id$")
    assert security.verify_password(hashed, password)
    assert not security.verify_password(hashed, password + "x")
    assert not security.verify_password("not-a-hash", password)
    assert not security.needs_rehash(hashed)
    # V-13: at least the OWASP Argon2id minimum (19 MiB, 2 iterations, parallelism 1).
    match = _PARAMS.match(hashed)
    assert match is not None
    memory_kib, iterations, parallelism = (int(group) for group in match.groups())
    assert memory_kib >= 19 * 1024
    assert iterations >= 2
    assert parallelism >= 1


def test_ut_sec_01_same_password_gives_different_salted_hashes() -> None:
    password = secrets.token_urlsafe(16)
    assert security.hash_password(password) != security.hash_password(password)


def test_dummy_verify_runs_a_real_verification() -> None:
    with mock.patch.object(security, "verify_password", wraps=security.verify_password) as spy:
        security.dummy_verify("anything")
    assert spy.call_count == 1


def test_ut_sec_02_csrf_token_is_hmac_of_the_session_id() -> None:
    session_id = uuid.uuid4()
    token = security.csrf_token(KEY, session_id)
    expected = hmac.new(KEY, str(session_id).encode(), hashlib.sha256).digest()
    assert base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)) == expected
    assert "=" not in token
    assert security.csrf_token_valid(KEY, session_id, token)


def test_ut_sec_02_token_of_another_session_or_key_fails() -> None:
    session_a, session_b = uuid.uuid4(), uuid.uuid4()
    token_a = security.csrf_token(KEY, session_a)
    assert not security.csrf_token_valid(KEY, session_b, token_a)
    assert not security.csrf_token_valid(secrets.token_bytes(32), session_a, token_a)
    assert not security.csrf_token_valid(KEY, session_a, "")
    assert not security.csrf_token_valid(KEY, session_a, "ünïcödé")


def test_ut_sec_02_comparison_is_constant_time() -> None:
    session_id = uuid.uuid4()
    token = security.csrf_token(KEY, session_id)
    with mock.patch.object(security.hmac, "compare_digest", wraps=hmac.compare_digest) as spy:
        assert security.csrf_token_valid(KEY, session_id, token)
    assert spy.call_count == 1


def test_session_tokens_are_256_bit_and_stored_as_sha256() -> None:
    token = security.new_session_token()
    assert len(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))) == 32
    digest = security.hash_session_token(token)
    assert digest == hashlib.sha256(token.encode()).digest()
    assert len(digest) == 32
    assert security.new_session_token() != token


def test_login_subject_hash_is_keyed_hmac_of_the_normalised_email() -> None:
    email = security.normalise_email("  Owner@Demo.INVALID ")
    assert email == "owner@demo.invalid"
    digest = security.login_subject_hash(KEY, email)
    assert digest == hmac.new(KEY, b"login:owner@demo.invalid", hashlib.sha256).hexdigest()
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert security.login_subject_hash(secrets.token_bytes(32), email) != digest
