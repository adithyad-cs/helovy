"""The S3 client and bucket checks (docs/04 §13, docs/05 §8).

boto3 is the single storage implementation: there is no filesystem fallback, and no
presigned or public URLs are ever created. Objects stay private; downloads are proxied
by the API after authorisation and SHA-256 checks (M5).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings

logger = logging.getLogger("app.storage")

_MISSING_BUCKET_CODES = {"404", "NoSuchBucket", "NotFound"}


class StorageError(RuntimeError):
    """Storage could not complete an operation; the message never contains credentials."""


def create_s3_client(settings: Settings) -> Any:
    """A boto3 S3 client for ``S3_ENDPOINT_URL`` with short timeouts and one attempt."""
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id.get_secret_value(),
        aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": settings.s3_addressing_style},
            connect_timeout=3,
            read_timeout=10,
            # Standard mode retries transient connection errors (for example a pooled
            # keep-alive connection that the server closed). Every call is idempotent.
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


def bucket_is_ready(client: Any, bucket: str) -> bool:
    """Readiness check: HeadBucket on the configured bucket (docs/07 E-02)."""
    try:
        client.head_bucket(Bucket=bucket)
    except (ClientError, BotoCoreError) as exc:
        logger.warning("storage readiness check failed: %s", type(exc).__name__)
        return False
    return True


@dataclass(frozen=True)
class BucketInitResult:
    bucket: str
    created: bool
    versioning: str  # "Enabled", "Suspended", "not enabled" or "not supported"


def _versioning_status(client: Any, bucket: str) -> str:
    try:
        status = client.get_bucket_versioning(Bucket=bucket).get("Status")
    except ClientError as exc:
        logger.info("bucket versioning status unavailable: %s", _error_code(exc))
        return "not supported"
    return str(status) if status else "not enabled"


def init_bucket(client: Any, bucket: str, region: str) -> BucketInitResult:
    """Create ``bucket`` if it is missing and enable versioning when the server supports it.

    Safe to re-run: an existing bucket is left unchanged and reported as ready (V-18).
    """
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        if _error_code(exc) not in _MISSING_BUCKET_CODES:
            raise StorageError(f"HeadBucket on {bucket} failed: {_error_code(exc)}") from exc
    except BotoCoreError as exc:
        raise StorageError(f"storage unreachable: {type(exc).__name__}") from exc
    else:
        return BucketInitResult(
            bucket, created=False, versioning=_versioning_status(client, bucket)
        )

    create_args: dict[str, Any] = {"Bucket": bucket}
    if region != "us-east-1":
        create_args["CreateBucketConfiguration"] = {"LocationConstraint": region}
    try:
        client.create_bucket(**create_args)
    except (ClientError, BotoCoreError) as exc:
        code = _error_code(exc) if isinstance(exc, ClientError) else type(exc).__name__
        raise StorageError(f"CreateBucket {bucket} failed: {code}") from exc

    try:
        client.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
    except ClientError as exc:
        logger.info("bucket versioning not enabled: %s", _error_code(exc))
        return BucketInitResult(bucket, created=True, versioning="not supported")
    return BucketInitResult(bucket, created=True, versioning=_versioning_status(client, bucket))
