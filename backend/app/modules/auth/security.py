"""Password hashing, session tokens and CSRF tokens (docs/12 §2-§4).

- Passwords: argon2-cffi ``PasswordHasher`` with its default (RFC 9106 low-memory) parameters,
  which exceed the OWASP Argon2id minimum (V-13; UT-SEC-01).
- Session tokens: 256-bit random, URL-safe; only their SHA-256 is stored.
- CSRF tokens: base64url(HMAC-SHA256(CSRF_SECRET, session ID)), compared in constant time
  (UT-SEC-02). The session ID is fed as its canonical text form (``str(uuid)``).
- Login subject hash: HMAC-SHA256(CSRF_SECRET, "login:" + normalised email), hex.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from functools import cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

SESSION_TOKEN_BYTES = 32

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


@cache
def _dummy_hash() -> str:
    # A fixed hash of a random value, created once per process; never matches a real input.
    return _hasher.hash(secrets.token_urlsafe(32))


def dummy_verify(password: str) -> None:
    """Spend the same work as a real verification, for unknown emails (docs/12 §2.2)."""
    verify_password(_dummy_hash(), password)


def new_session_token() -> str:
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_session_token(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def csrf_token(key: bytes, session_id: uuid.UUID) -> str:
    digest = hmac.new(key, str(session_id).encode("ascii"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def csrf_token_valid(key: bytes, session_id: uuid.UUID, presented: str) -> bool:
    expected = csrf_token(key, session_id).encode("ascii")
    return hmac.compare_digest(expected, presented.encode("utf-8", errors="replace"))


def normalise_email(email: str) -> str:
    return email.strip().lower()


def login_subject_hash(key: bytes, normalised_email: str) -> str:
    message = ("login:" + normalised_email).encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()
