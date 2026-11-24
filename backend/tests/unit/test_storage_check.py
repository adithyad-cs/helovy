"""``check_app_storage`` (Render preparation): the app's credentials must reach a versioned
bucket and must not be able to administer it. botocore's Stubber stands in for the server;
the real-server behaviour is covered in tests/integration/test_storage_check.py.
"""

from __future__ import annotations

from typing import Any

import boto3
import pytest
from botocore.config import Config
from botocore.stub import Stubber

from app.modules.storage.client import check_app_storage

BUCKET = "ps5-documents-staging"


@pytest.fixture
def stubbed() -> Any:
    client = boto3.client(
        "s3",
        endpoint_url="http://storage.invalid:8333",
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        config=Config(s3={"addressing_style": "path"}),
    )
    with Stubber(client) as stubber:
        yield client, stubber


def _ready(stubber: Stubber, status: str | None = "Enabled") -> None:
    stubber.add_response("head_bucket", {}, {"Bucket": BUCKET})
    stubber.add_response(
        "get_bucket_versioning", {"Status": status} if status else {}, {"Bucket": BUCKET}
    )


def _denied(stubber: Stubber, operation: str) -> None:
    stubber.add_client_error(operation, "AccessDenied", "Access Denied", 403)


def test_restricted_credentials_on_a_versioned_bucket_pass(stubbed: Any) -> None:
    client, stubber = stubbed
    _ready(stubber)
    _denied(stubber, "put_bucket_versioning")
    _denied(stubber, "put_bucket_acl")
    result = check_app_storage(client, BUCKET)
    assert result.ok
    assert result.probes == {
        "PutBucketVersioning": "refused (AccessDenied)",
        "PutBucketAcl": "refused (AccessDenied)",
    }
    stubber.assert_no_pending_responses()


@pytest.mark.parametrize("allowed", ["put_bucket_versioning", "put_bucket_acl"])
def test_credentials_that_can_administer_the_bucket_fail(stubbed: Any, allowed: str) -> None:
    client, stubber = stubbed
    _ready(stubber)
    for operation in ("put_bucket_versioning", "put_bucket_acl"):
        if operation == allowed:
            stubber.add_response(operation, {})
        else:
            _denied(stubber, operation)
    result = check_app_storage(client, BUCKET)
    assert result.can_administer
    assert not result.ok


def test_bucket_without_versioning_fails(stubbed: Any) -> None:
    client, stubber = stubbed
    _ready(stubber, status=None)
    _denied(stubber, "put_bucket_versioning")
    _denied(stubber, "put_bucket_acl")
    result = check_app_storage(client, BUCKET)
    assert result.versioning == "not enabled"
    assert not result.can_administer
    assert not result.ok


def test_missing_bucket_fails_without_probing(stubbed: Any) -> None:
    client, stubber = stubbed
    stubber.add_client_error("head_bucket", "404", "Not Found", 404)
    result = check_app_storage(client, BUCKET)
    assert (result.ready, result.versioning, result.probes, result.ok) == (
        False,
        "unknown",
        {},
        False,
    )
    stubber.assert_no_pending_responses()
