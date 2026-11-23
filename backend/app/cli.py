"""Administrative command line (docs/05 §8): ``python -m app.cli <command>``.

Implemented in M0: ``init-dev-storage``. ``create-demo-account`` arrives in M1 and
``template-hash`` in M4.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from app.core.config import ConfigError, load_settings
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="HIVE DOCS admin CLI")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "init-dev-storage",
        help="create the S3_BUCKET bucket for local development or tests (safe to re-run)",
    )
    args = parser.parse_args(argv)
    if args.command == "init-dev-storage":
        return _init_dev_storage()
    parser.error(f"unknown command {args.command!r}")  # exits with status 2


if __name__ == "__main__":
    sys.exit(main())
