"""The SeaweedFS verification gate (docs/05 §14.1), automated against the test bucket.

- V-18: ``init-dev-storage`` creates the bucket and is safe to re-run; refused in production.
- V-19: the application's credentials and boto3 client write an object and read it back byte
  for byte (equal SHA-256), and HeadBucket succeeds.
- V-08: unauthenticated GET and PUT are refused.
- docs/12 §8: the credentials are limited to their own bucket.

V-07 (pinned image and command) is checked on the running compose service; the result is
recorded in PROGRESS.md. The development bucket is checked by running the CLI with ``.env``.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import subprocess
import sys
import uuid
from collections.abc import Iterator
from typing import Any

import boto3
import httpx
import pytest
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import REPO_ROOT, Settings

BACKEND_DIR = REPO_ROOT / "backend"
OTHER_BUCKET = "ps5-documents-dev"


def _run_cli(*, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **(extra_env or {})}
    return subprocess.run(
        [sys.executable, "-m", "app.cli", "init-dev-storage"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _empty_and_delete_bucket(s3: Any, bucket: str) -> None:
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError:
        return
    paginator = s3.get_paginator("list_object_versions")
    for page in paginator.paginate(Bucket=bucket):
        for item in page.get("Versions", []) + page.get("DeleteMarkers", []):
            s3.delete_object(Bucket=bucket, Key=item["Key"], VersionId=item["VersionId"])
    s3.delete_bucket(Bucket=bucket)


@pytest.fixture
def stored_object(s3: Any, test_bucket: str) -> Iterator[tuple[str, bytes]]:
    key = f"m0-gate/{uuid.uuid4()}.bin"
    data = secrets.token_bytes(256 * 1024)
    s3.put_object(Bucket=test_bucket, Key=key, Body=data, ContentType="application/octet-stream")
    yield key, data
    s3.delete_object(Bucket=test_bucket, Key=key)


def test_v18_init_dev_storage_creates_bucket_and_is_safe_to_rerun(
    settings: Settings, s3: Any
) -> None:
    _empty_and_delete_bucket(s3, settings.s3_bucket)

    first = _run_cli()
    assert first.returncode == 0, first.stderr
    assert f"bucket {settings.s3_bucket} created" in first.stdout
    assert f"bucket {settings.s3_bucket} is ready" in first.stdout
    s3.head_bucket(Bucket=settings.s3_bucket)

    marker = f"m0-gate/rerun-{uuid.uuid4()}.txt"
    s3.put_object(Bucket=settings.s3_bucket, Key=marker, Body=b"kept")

    second = _run_cli()
    assert second.returncode == 0, second.stderr
    assert "already exists (left unchanged)" in second.stdout
    assert f"bucket {settings.s3_bucket} is ready" in second.stdout
    # The re-run changed nothing: existing objects are still there.
    assert s3.get_object(Bucket=settings.s3_bucket, Key=marker)["Body"].read() == b"kept"
    s3.delete_object(Bucket=settings.s3_bucket, Key=marker)


def test_v18_init_dev_storage_refuses_production() -> None:
    # An unreachable endpoint proves the refusal happens before storage is contacted.
    result = _run_cli(extra_env={"APP_ENV": "production", "S3_ENDPOINT_URL": "http://127.0.0.1:1"})
    assert result.returncode == 2
    assert "refusing to run with APP_ENV=production" in result.stderr


def test_v19_authenticated_put_and_get_round_trip(
    s3: Any, test_bucket: str, stored_object: tuple[str, bytes]
) -> None:
    s3.head_bucket(Bucket=test_bucket)
    key, data = stored_object
    read_back = s3.get_object(Bucket=test_bucket, Key=key)["Body"].read()
    assert read_back == data
    assert hashlib.sha256(read_back).hexdigest() == hashlib.sha256(data).hexdigest()
    assert s3.head_object(Bucket=test_bucket, Key=key)["ContentLength"] == len(data)


def test_v08_anonymous_get_and_put_are_refused(
    settings: Settings, s3: Any, test_bucket: str, stored_object: tuple[str, bytes]
) -> None:
    key, data = stored_object
    object_url = f"{settings.s3_endpoint_url}/{test_bucket}/{key}"
    with httpx.Client(timeout=5) as anonymous:
        assert anonymous.get(object_url).status_code == 403
        assert anonymous.put(object_url, content=b"tampered").status_code == 403
        assert anonymous.put(f"{settings.s3_endpoint_url}/{test_bucket}/new.bin").status_code == 403
        assert anonymous.get(f"{settings.s3_endpoint_url}/{test_bucket}").status_code == 403
        assert anonymous.get(f"{settings.s3_endpoint_url}/").status_code == 403
    # The refused PUT changed nothing.
    assert s3.get_object(Bucket=test_bucket, Key=key)["Body"].read() == data


def test_v08_unsigned_boto3_client_is_refused(
    settings: Settings, test_bucket: str, stored_object: tuple[str, bytes]
) -> None:
    key, _ = stored_object
    unsigned = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        config=Config(signature_version=UNSIGNED, s3={"addressing_style": "path"}),
    )
    with pytest.raises(ClientError) as caught:
        unsigned.get_object(Bucket=test_bucket, Key=key)
    assert caught.value.response["Error"]["Code"] == "AccessDenied"


def test_credentials_are_limited_to_their_own_bucket(s3: Any) -> None:
    with pytest.raises(ClientError) as head:
        s3.head_bucket(Bucket=OTHER_BUCKET)
    assert head.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    with pytest.raises(ClientError) as put:
        s3.put_object(Bucket=OTHER_BUCKET, Key="cross-bucket.bin", Body=b"x")
    assert put.value.response["Error"]["Code"] == "AccessDenied"
