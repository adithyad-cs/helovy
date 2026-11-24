"""``check-storage`` against the real SeaweedFS test bucket (Render preparation).

The local test identity deliberately holds ``Admin:ps5-documents-test`` (init-dev-storage
creates its bucket with it), so the check must report that these credentials can administer
the bucket and exit 1. The probes only (re)enable versioning and keep the bucket private.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.modules.storage.client import check_app_storage

BACKEND = Path(__file__).resolve().parents[2]


def test_check_detects_admin_rights_of_the_local_test_identity(
    s3: Any, settings: Settings, test_bucket: str
) -> None:
    result = check_app_storage(s3, test_bucket)
    assert result.ready
    assert result.versioning == "Enabled"
    assert result.probes["PutBucketVersioning"] == "ALLOWED"
    assert result.can_administer
    assert not result.ok


def test_cli_fails_and_never_prints_the_keys(settings: Settings, test_bucket: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app.cli", "check-storage"],
        cwd=BACKEND,
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert f"bucket {test_bucket} reachable with the app credentials: yes" in output
    assert "versioning: Enabled" in output
    assert "can administer the bucket" in output
    for secret in (
        settings.s3_access_key_id.get_secret_value(),
        settings.s3_secret_access_key.get_secret_value(),
    ):
        assert secret not in output


def test_cli_reports_an_unreachable_bucket(settings: Settings) -> None:
    env = dict(os.environ, S3_ENDPOINT_URL="http://127.0.0.1:1")
    result = subprocess.run(
        [sys.executable, "-m", "app.cli", "check-storage"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 1
    assert "reachable with the app credentials: NO" in result.stdout
