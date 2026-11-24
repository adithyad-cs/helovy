"""Deployment files (Render staging preparation): image contents, migrations, Blueprint.

Static checks that need no Docker daemon and no network:

- the application image ships the Alembic configuration and every migration, listens on
  ``$PORT``, runs one worker as a non-root user;
- the migration chain has one head and ``alembic.ini`` works from any directory;
- ``render.yaml`` keeps the security boundaries: Singapore, PostgreSQL 16 database ``ps5``
  owned by ``ps5_migrator``, no secret values, a private storage service with a disk, the
  ``/readyz`` health check and the pre-deploy migration;
- the Render storage image is SeaweedFS 4.54 pinned to the same digest as Compose and binds
  only its S3 gateway beyond localhost.

The full image build and the storage behaviour were verified separately (PROGRESS.md).
"""

from __future__ import annotations

import configparser
import fnmatch
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
DOCKERFILE = (REPO / "Dockerfile").read_text(encoding="utf-8")
DOCKERIGNORE = (REPO / ".dockerignore").read_text(encoding="utf-8")
STORAGE_DOCKERFILE = (REPO / "deploy/render/seaweedfs/Dockerfile").read_text(encoding="utf-8")
COMPOSE = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
BLUEPRINT: dict[str, Any] = yaml.safe_load((REPO / "render.yaml").read_text(encoding="utf-8"))
MIGRATIONS = sorted(p.name for p in (BACKEND / "alembic/versions").glob("0*.py"))


# --- Application image ---------------------------------------------------------------------


def _ignored(path: str) -> bool:
    """Docker's .dockerignore semantics for these simple patterns: the last match wins."""
    ignored = False
    for raw in DOCKERIGNORE.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        negate = line.startswith("!")
        pattern = line[1:] if negate else line
        pattern = pattern.rstrip("/")
        candidates = {pattern, pattern + "/**"}
        if pattern.startswith("**/"):
            candidates |= {pattern[3:], pattern[3:] + "/**"}
        parts = path.split("/")
        prefixes = ["/".join(parts[: i + 1]) for i in range(len(parts))]
        if any(fnmatch.fnmatchcase(p, c) for p in prefixes for c in candidates):
            ignored = not negate
    return ignored


@pytest.mark.parametrize(
    "path",
    ["backend/alembic.ini", "backend/alembic/env.py", "backend/alembic/script.py.mako"]
    + [f"backend/alembic/versions/{name}" for name in MIGRATIONS],
)
def test_build_context_includes_alembic_files(path: str) -> None:
    assert (REPO / path).is_file()
    assert not _ignored(path)


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.test",
        "deploy/seaweedfs/s3.json",
        "deploy/render/seaweedfs/s3.json",
        "s3.json",
        "backend/tests/unit/test_deployment_config.py",
        "backend/scripts/enter_demo_data.py",
        "backend/alembic/__pycache__/env.cpython-312.pyc",
        "backend/app/static/index.html",
        "render.yaml",
    ],
)
def test_build_context_excludes_secrets_tests_and_tooling(path: str) -> None:
    assert _ignored(path)


def test_image_copies_alembic_files() -> None:
    assert "COPY backend/alembic.ini ./alembic.ini" in DOCKERFILE
    assert "COPY backend/alembic ./alembic" in DOCKERFILE


def test_image_listens_on_port_with_one_worker_as_non_root() -> None:
    cmd = re.search(r"^CMD (.+)$", DOCKERFILE, re.MULTILINE)
    assert cmd is not None
    command = cmd.group(1)
    assert "exec uvicorn app.main:app" in command
    assert '--port \\"${PORT:-8000}\\"' in command
    assert "--host 0.0.0.0" in command
    assert "--workers 1" in command
    assert "--no-proxy-headers" in command
    runtime = DOCKERFILE.split("AS runtime", 1)[1]
    assert re.search(r"^USER 10001$", runtime, re.MULTILINE)
    after_user = runtime.split("USER 10001", 1)[1]
    assert "RUN " not in after_user  # nothing runs as root after switching user


def test_alembic_ini_works_from_any_working_directory() -> None:
    parser = configparser.ConfigParser()
    parser.read(BACKEND / "alembic.ini")
    assert parser.get("alembic", "script_location", raw=True) == "%(here)s/alembic"
    assert parser.get("alembic", "prepend_sys_path", raw=True) == "%(here)s"


def test_migration_chain_has_one_head() -> None:
    script = ScriptDirectory.from_config(Config(str(BACKEND / "alembic.ini")))
    assert script.get_heads() == ["0005_app_role_privileges"]
    chain = [revision.revision for revision in script.walk_revisions()]
    assert chain == [
        "0005_app_role_privileges",
        "0004_issuance",
        "0003_documents",
        "0002_parties",
        "0001_identity",
    ]


# --- Render Blueprint ----------------------------------------------------------------------

SERVICES = {service["name"]: service for service in BLUEPRINT["services"]}
DATABASES = {database["name"]: database for database in BLUEPRINT["databases"]}
WEB = SERVICES["hive-docs-staging"]
STORAGE = SERVICES["hive-docs-staging-storage"]
DATABASE = DATABASES["hive-docs-staging-db"]
WEB_ENV = {entry["key"]: entry for entry in WEB["envVars"]}
SECRET_KEYS = {"DATABASE_URL", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_ENDPOINT_URL"}


def test_blueprint_has_exactly_the_three_staging_resources() -> None:
    assert set(BLUEPRINT) == {"databases", "services"}
    assert set(SERVICES) == {"hive-docs-staging", "hive-docs-staging-storage"}
    assert set(DATABASES) == {"hive-docs-staging-db"}


def test_everything_runs_in_singapore() -> None:
    for resource in [*BLUEPRINT["services"], *BLUEPRINT["databases"]]:
        assert resource["region"] == "singapore", resource["name"]


def test_database_is_postgres_16_named_ps5_owned_by_the_migrator_and_closed() -> None:
    assert DATABASE["postgresMajorVersion"] == "16"
    assert DATABASE["databaseName"] == "ps5"
    assert DATABASE["user"] == "ps5_migrator"
    assert DATABASE["ipAllowList"] == []


def test_web_service_health_check_and_pre_deploy_migration() -> None:
    assert WEB["type"] == "web"
    assert WEB["runtime"] == "docker"
    assert WEB["dockerfilePath"] == "./Dockerfile"
    assert WEB["healthCheckPath"] == "/readyz"
    assert WEB["preDeployCommand"] == "alembic -c /app/backend/alembic.ini upgrade head"
    assert WEB["numInstances"] == 1  # in-memory rate limits and render pool: one process
    assert "scaling" not in WEB


def test_web_environment_is_production_and_holds_no_secret_values() -> None:
    assert WEB_ENV["APP_ENV"]["value"] == "production"
    assert WEB_ENV["APP_ORIGIN"]["fromService"] == {
        "name": "hive-docs-staging",
        "type": "web",
        "envVarKey": "RENDER_EXTERNAL_URL",
    }
    assert WEB_ENV["MIGRATION_DATABASE_URL"]["fromDatabase"] == {
        "name": "hive-docs-staging-db",
        "property": "connectionString",
    }
    for key in SECRET_KEYS:
        assert WEB_ENV[key] == {"key": key, "sync": False}, key
    assert WEB_ENV["CSRF_SECRET"] == {"key": "CSRF_SECRET", "generateValue": True}
    assert "PORT" not in WEB_ENV  # Render sets it; the image falls back to 8000
    assert "CLIENT_IP_HEADER" not in WEB_ENV  # unverified on Render (V-11): socket address


def test_app_role_url_is_never_the_default_users_connection_string() -> None:
    # fromDatabase connectionString always carries the default user (ps5_migrator).
    assert "fromDatabase" not in WEB_ENV["DATABASE_URL"]


def test_no_literal_value_looks_like_a_secret() -> None:
    allowed = {
        "APP_ENV": "production",
        "S3_REGION": "us-east-1",
        "S3_BUCKET": "ps5-documents-staging",
        "S3_ADDRESSING_STYLE": "path",
        "RENDER_WORKERS": "2",
        "RENDER_TIMEOUT_S": "20",
        "LOG_LEVEL": "INFO",
    }
    literal = {key: entry["value"] for key, entry in WEB_ENV.items() if "value" in entry}
    assert literal == allowed
    text = (REPO / "render.yaml").read_text(encoding="utf-8")
    # Only <placeholder> credentials may appear (in comments).
    assert not re.search(r"postgres(ql)?://[^\s:/@]+:(?!<)[^\s@]+@", text)
    assert re.search(r"postgres(ql)?://[^\s:/@]+:(?!<)[^\s@]+@", "postgres://u:real@h/db")
    assert "secretKey" not in text and "accessKey" not in text


def test_storage_is_a_private_service_with_a_persistent_disk() -> None:
    assert STORAGE["type"] == "pserv"  # no public URL
    assert STORAGE["runtime"] == "docker"
    assert STORAGE["dockerfilePath"] == "./deploy/render/seaweedfs/Dockerfile"
    assert STORAGE["dockerContext"] == "./deploy/render/seaweedfs"
    assert STORAGE["numInstances"] == 1
    assert STORAGE["disk"]["mountPath"] == "/data"
    assert "envVars" not in STORAGE  # its only secret is the s3.json secret file
    assert "ipAllowList" not in STORAGE and "domains" not in STORAGE


# --- Render storage image ------------------------------------------------------------------


def test_storage_image_is_seaweedfs_454_pinned_like_compose() -> None:
    base = re.search(r"^FROM (\S+)$", STORAGE_DOCKERFILE, re.MULTILINE)
    assert base is not None
    image = base.group(1)
    assert image.startswith("chrislusf/seaweedfs:4.54@sha256:")
    assert f"image: {image}" in COMPOSE


def test_storage_command_exposes_only_the_s3_gateway() -> None:
    command = re.search(r"^CMD \[(.+?)\]$", STORAGE_DOCKERFILE, re.MULTILINE | re.DOTALL)
    assert command is not None
    args = re.findall(r'"([^"]+)"', command.group(1))
    assert args[0] == "server"
    for flag in (
        "-ip=127.0.0.1",
        "-ip.bind=127.0.0.1",
        "-s3.ip.bind=0.0.0.0",
        "-s3",
        "-s3.port=8333",
        "-s3.port.iceberg=0",
        "-s3.port.lance=0",
        "-s3.config=/etc/secrets/s3.json",
        "-s3.autoCreateBucket=false",
        "-s3.iam=false",
        "-master.telemetry=false",
    ):
        assert flag in args, flag
    assert not any(a.startswith(("-webdav", "-sftp", "-iam", "-metricsPort")) for a in args)
    assert "COPY" not in STORAGE_DOCKERFILE and "ADD " not in STORAGE_DOCKERFILE


def test_storage_build_context_sends_nothing() -> None:
    ignore = (REPO / "deploy/render/seaweedfs/.dockerignore").read_text(encoding="utf-8")
    assert [line for line in ignore.splitlines() if line and not line.startswith("#")] == ["*"]


def test_storage_identity_example_gives_the_app_no_admin_rights() -> None:
    import json

    example = json.loads(
        (REPO / "deploy/render/seaweedfs/s3.example.json").read_text(encoding="utf-8")
    )
    identities = example["identities"]
    assert [identity["name"] for identity in identities] == ["hive-docs-app"]
    assert sorted(identities[0]["actions"]) == [
        "List:ps5-documents-staging",
        "Read:ps5-documents-staging",
        "Write:ps5-documents-staging",
    ]
    for credential in identities[0]["credentials"]:
        assert credential["accessKey"].startswith("<")
        assert credential["secretKey"].startswith("<")
