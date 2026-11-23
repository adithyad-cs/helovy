"""Administrative command line (docs/05 §8): ``python -m app.cli <command>``.

Implemented: ``init-dev-storage`` (M0) and ``create-demo-account`` (M1). ``template-hash``
arrives in M4.

``create-demo-account`` connects with the restricted app role (``DATABASE_URL``; docs/06 §11).
The password comes from ``DEMO_ACCOUNT_PASSWORD`` (set only for that one command) or from a
hidden prompt, and is never printed or logged (docs/12 §2.1).
"""

from __future__ import annotations

import argparse
import getpass
import os
import re
import sys
from collections.abc import Sequence

from app.core.clock import SystemClock
from app.core.config import ConfigError, load_settings
from app.core.db import create_db_engine, create_session_factory
from app.modules.auth.security import normalise_email
from app.modules.auth.service import (
    PASSWORD_MAX,
    PASSWORD_MIN,
    AccountExistsError,
    create_account,
)
from app.modules.storage.client import StorageError, create_s3_client, init_bucket

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2


def _init_dev_storage() -> int:
    """Create ``S3_BUCKET`` if missing; safe to re-run (V-18); refused in production."""
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"init-dev-storage: {exc}", file=sys.stderr)
        return EXIT_FAILED
    if settings.app_env == "production":
        print(
            "init-dev-storage: refusing to run with APP_ENV=production; "
            "production buckets are created and configured by the operator (docs/05 §13).",
            file=sys.stderr,
        )
        return EXIT_REFUSED
    try:
        result = init_bucket(create_s3_client(settings), settings.s3_bucket, settings.s3_region)
    except StorageError as exc:
        print(f"init-dev-storage: {exc}", file=sys.stderr)
        return EXIT_FAILED
    action = "created" if result.created else "already exists (left unchanged)"
    print(f"init-dev-storage: bucket {result.bucket} {action}; versioning: {result.versioning}")
    print(f"init-dev-storage: bucket {result.bucket} is ready")
    return EXIT_OK


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")  # docs/09 §4.2


def _read_password() -> str | None:
    from_env = os.environ.get("DEMO_ACCOUNT_PASSWORD")
    if from_env is not None:
        return from_env
    if not sys.stdin.isatty():
        return None
    first = getpass.getpass("Password for the new account (at least 12 characters): ")
    second = getpass.getpass("Repeat the password: ")
    return first if first == second else ""


def _create_demo_account(email: str, name: str, org: str) -> int:
    """One organization, one user, an owner membership and ``account.created`` (docs/05 §8)."""
    email = normalise_email(email)
    name, org = name.strip(), org.strip()
    problems = []
    if not (3 <= len(email) <= 254 and _EMAIL.match(email)):
        problems.append("--email must be a valid address of 3-254 characters")
    if not 1 <= len(name) <= 120:
        problems.append("--name must be 1-120 characters")
    if not 1 <= len(org) <= 200:
        problems.append("--org must be 1-200 characters")
    password = _read_password()
    if password is None:
        problems.append("set DEMO_ACCOUNT_PASSWORD or run in a terminal to be prompted")
    elif password == "":
        problems.append("the two passwords did not match")
    elif not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        problems.append(f"the password must be {PASSWORD_MIN}-{PASSWORD_MAX} characters")
    if problems:
        print("create-demo-account: " + "; ".join(problems), file=sys.stderr)
        return EXIT_REFUSED
    assert password is not None  # noqa: S101 - narrowed by the checks above
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"create-demo-account: {exc}", file=sys.stderr)
        return EXIT_FAILED
    engine = create_db_engine(settings)
    try:
        with create_session_factory(engine)() as db:
            org_id, user_id = create_account(
                db,
                now=SystemClock().now(),
                email=email,
                display_name=name,
                org_name=org,
                password=password,
            )
    except AccountExistsError:
        print("create-demo-account: an account with this email already exists", file=sys.stderr)
        return EXIT_REFUSED
    except Exception as exc:  # noqa: BLE001 - report the failure class, never its details
        print(f"create-demo-account: failed ({type(exc).__name__})", file=sys.stderr)
        return EXIT_FAILED
    finally:
        engine.dispose()
    print(f"create-demo-account: created organization {org_id} with owner user {user_id}")
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="HIVE DOCS admin CLI")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "init-dev-storage",
        help="create the S3_BUCKET bucket for local development or tests (safe to re-run)",
    )
    account = commands.add_parser(
        "create-demo-account",
        help="create one organization, one owner user and its membership (docs/05 §8)",
    )
    account.add_argument("--email", required=True)
    account.add_argument("--name", required=True, help="display name of the owner")
    account.add_argument("--org", required=True, help="organization name")
    args = parser.parse_args(argv)
    if args.command == "init-dev-storage":
        return _init_dev_storage()
    if args.command == "create-demo-account":
        return _create_demo_account(args.email, args.name, args.org)
    parser.error(f"unknown command {args.command!r}")  # exits with status 2


if __name__ == "__main__":
    sys.exit(main())
