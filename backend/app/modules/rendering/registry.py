"""The template registry: template ID → directory and expected SHA-256 (docs/09 §11).

The hash covers the template directory: files sorted by relative POSIX path; for each file
the hash is fed ``path + "\\0" + hex SHA-256 of the file bytes + "\\n"``. A registered
version is immutable: any change to its files becomes a new version (``classic@2``).
``python -m app.cli template-hash classic@1`` prints the value to register.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


@dataclass(frozen=True)
class RegisteredTemplate:
    template_id: str
    directory: Path
    sha256: str


REGISTRY: dict[str, RegisteredTemplate] = {
    "classic@1": RegisteredTemplate(
        "classic@1",
        TEMPLATES_DIR / "invoice" / "classic" / "v1",
        "3dba1d0e1295feb0d9c9a3c50173655641d3e8860b722ade626444410c8b84e7",
    ),
}


class UnknownTemplateError(KeyError):
    """The template ID is not registered."""


def template_hash(directory: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(
        (path for path in directory.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(directory).as_posix(),
    )
    for path in files:
        relative = path.relative_to(directory).as_posix()
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        digest.update(f"{relative}\0{file_hash}\n".encode())
    return digest.hexdigest()


def get(template_id: str) -> RegisteredTemplate:
    try:
        return REGISTRY[template_id]
    except KeyError:
        raise UnknownTemplateError(template_id) from None


def matches(template_id: str) -> bool:
    """True when the files on disk hash to the registered value."""
    entry = get(template_id)
    return entry.directory.is_dir() and template_hash(entry.directory) == entry.sha256


def all_match() -> bool:
    return all(matches(template_id) for template_id in REGISTRY)
