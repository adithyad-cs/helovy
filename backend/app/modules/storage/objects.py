"""Private object storage for issued PDFs (docs/04 §13; docs/09 §11; docs/12 §8).

Only this module talks to S3, and only the documents module calls it (docs/04 §3). Objects
are private: there are no public ACLs and no presigned URLs. Keys are
``orgs/{org_id}/documents/{document_id}/final-{artifact_id}.pdf``.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger("app.storage")

_MISSING_CODES = {"NoSuchKey", "404", "NotFound"}


class StorageUnavailableError(RuntimeError):
    """Storage could not be reached or refused the operation."""


class ObjectMissingError(RuntimeError):
    """The object does not exist."""


@dataclass(frozen=True)
class PutResult:
    version_id: str | None


def final_pdf_key(org_id: uuid.UUID, document_id: uuid.UUID, artifact_id: uuid.UUID) -> str:
    return f"orgs/{org_id}/documents/{document_id}/final-{artifact_id}.pdf"


def put_pdf(client: Any, bucket: str, key: str, data: bytes) -> PutResult:
    try:
        response = client.put_object(
            Bucket=bucket, Key=key, Body=data, ContentType="application/pdf"
        )
    except (ClientError, BotoCoreError) as exc:
        logger.error("storage PUT failed: %s", type(exc).__name__)
        raise StorageUnavailableError(type(exc).__name__) from None
    version = response.get("VersionId")
    return PutResult(version_id=str(version) if version and version != "null" else None)


def get_object(client: Any, bucket: str, key: str, version_id: str | None = None) -> bytes:
    arguments: dict[str, Any] = {"Bucket": bucket, "Key": key}
    if version_id:
        arguments["VersionId"] = version_id
    try:
        response = client.get_object(**arguments)
        data: bytes = response["Body"].read()
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in _MISSING_CODES:
            raise ObjectMissingError(key) from None
        logger.error("storage GET failed: %s", code or type(exc).__name__)
        raise StorageUnavailableError(code) from None
    except BotoCoreError as exc:
        logger.error("storage GET failed: %s", type(exc).__name__)
        raise StorageUnavailableError(type(exc).__name__) from None
    return data
