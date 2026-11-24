"""Administrative command line (docs/05 §8): ``python -m app.cli <command>``.

Implemented: ``init-dev-storage`` (M0), ``create-demo-account`` (M1), ``template-hash``
(M4) and ``check-storage`` (Render staging preparation, docs/DEPLOYMENT_RENDER.md).

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
from app.modules.storage.client import (
    StorageError,
    check_app_storage,
    create_s3_client,
    init_bucket,
)

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


def _template_hash(template_id: str) -> int:
    """Print the SHA-256 over a template's files, for the registry (docs/09 §11)."""
    from app.modules.rendering import registry

    try:
        entry = registry.get(template_id)
    except registry.UnknownTemplateError:
        print(f"template-hash: unknown template {template_id!r}", file=sys.stderr)
        return EXIT_REFUSED
    print(registry.template_hash(entry.directory))
    return EXIT_OK


def _check_storage() -> int:
    """Check the application's own S3 access: bucket reachable, versioning on, no admin rights.

    Meant for staging and production, where the application identity must hold only Read,
    Write and List on its bucket (the local development identities also hold Admin, so this
    command reports them as able to administer the bucket). Never prints credentials.
    """
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"check-storage: {exc}", file=sys.stderr)
        return EXIT_FAILED
    result = check_app_storage(create_s3_client(settings), settings.s3_bucket)
    reachable = "yes" if result.ready else "NO"
    print(f"check-storage: bucket {result.bucket} reachable with the app credentials: {reachable}")
    if not result.ready:
        print(
            "check-storage: FAILED: create the bucket and check S3_ENDPOINT_URL, S3_BUCKET and "
            "the app identity's keys",
            file=sys.stderr,
        )
        return EXIT_FAILED
    print(f"check-storage: versioning: {result.versioning}")
    for probe, outcome in result.probes.items():
        print(f"check-storage: {probe} with the app credentials: {outcome}")
    if result.can_administer:
        print(
            "check-storage: FAILED: the app credentials can administer the bucket; give the "
            "app identity only Read, Write and List on it",
            file=sys.stderr,
        )
        return EXIT_FAILED
    if result.versioning != "Enabled":
        print("check-storage: FAILED: enable versioning on the bucket", file=sys.stderr)
        return EXIT_FAILED
    print("check-storage: OK")
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
    hashing = commands.add_parser(
        "template-hash", help="print the SHA-256 over a template's files (docs/09 §11)"
    )
    hashing.add_argument("template_id")
    commands.add_parser(
        "check-storage",
        help="check the app S3 credentials: versioned bucket reachable, no admin rights",
    )
    args = parser.parse_args(argv)
    if args.command == "template-hash":
        return _template_hash(args.template_id)
    if args.command == "init-dev-storage":
        return _init_dev_storage()
    if args.command == "create-demo-account":
        return _create_demo_account(args.email, args.name, args.org)
    if args.command == "check-storage":
        return _check_storage()
    parser.error(f"unknown command {args.command!r}")  # exits with status 2


if __name__ == "__main__":
    sys.exit(main())
