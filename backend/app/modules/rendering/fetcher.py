"""The restricted URL fetcher (docs/12 §9; docs/04 §11; UT-SEC-03).

WeasyPrint may load only files inside the bundled assets directory (the Noto fonts). Every
other URL is refused: ``http:``, ``https:``, ``ftp:``, ``data:``, any ``file:`` path outside
the assets directory, and path traversal. Rendering therefore never touches the network.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlsplit

from weasyprint.urls import URLFetcher, URLFetcherResponse

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


class FetchRefusedError(ValueError):
    """A resource outside the bundled assets was requested."""


def resolve_asset(url: str, root: Path = ASSETS_DIR) -> Path:
    """The bundled file a ``file:`` URL names, or FetchRefusedError."""
    parts = urlsplit(url)
    if parts.scheme != "file" or parts.netloc not in ("", "localhost"):
        raise FetchRefusedError(f"refused scheme or host in {url[:80]!r}")
    if parts.query or parts.fragment:
        raise FetchRefusedError("refused query or fragment")
    raw = unquote(parts.path)
    if "\x00" in raw or ".." in Path(raw).parts:
        raise FetchRefusedError("refused path traversal")
    path = Path(raw).resolve()
    base = root.resolve()
    if base not in path.parents or not path.is_file():
        raise FetchRefusedError("refused path outside the assets directory")
    return path


class RestrictedFetcher(URLFetcher):  # type: ignore[misc]  # weasyprint is untyped
    """Serves bundled asset files only; refuses everything else."""

    def __init__(self, root: Path = ASSETS_DIR) -> None:
        super().__init__(timeout=1, allowed_protocols=("file",), allow_redirects=False)
        self.root = root.resolve()
        self.refused: list[str] = []

    def fetch(self, url: str, headers: object = None) -> URLFetcherResponse:
        try:
            path = resolve_asset(url, self.root)
        except FetchRefusedError:
            self.refused.append(url[:200])
            raise
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return URLFetcherResponse(url, path.read_bytes(), {"Content-Type": mime})
