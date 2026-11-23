"""UT-SEC-03 (docs/11 §2.1): the restricted URL fetcher; IT-PDF-05 part 1 (no fetch of an
external URL during a render; docs/12 §9)."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import weasyprint

from app.modules.rendering.fetcher import ASSETS_DIR, FetchRefusedError, RestrictedFetcher

FONT = ASSETS_DIR / "fonts" / "NotoSans-Regular.ttf"


def test_ut_sec_03_bundled_asset_is_served() -> None:
    response = RestrictedFetcher().fetch(FONT.as_uri())
    assert response.read() == FONT.read_bytes()


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/font.ttf",
        "https://fonts.example.invalid/font.ttf",
        "ftp://example.invalid/font.ttf",
        "data:text/plain;base64,SGVsbG8=",
        "file:///etc/passwd",
        (ASSETS_DIR / "fonts" / ".." / ".." / "fetcher.py").as_uri(),
        ASSETS_DIR.as_uri() + "/fonts/../../fetcher.py",
        ASSETS_DIR.as_uri() + "/fonts/%2e%2e/%2e%2e/fetcher.py",
        ASSETS_DIR.as_uri() + "/fonts/missing.ttf",
        FONT.as_uri() + "?x=1",
        "file://remote-host" + str(FONT),
        "javascript:alert(1)",
    ],
)
def test_ut_sec_03_everything_else_is_refused(url: str) -> None:
    fetcher = RestrictedFetcher()
    with pytest.raises((FetchRefusedError, ValueError)):
        fetcher.fetch(url)


def test_symlink_out_of_assets_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "assets"
    root.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("x")
    (root / "link.txt").symlink_to(secret)
    with pytest.raises(FetchRefusedError):
        RestrictedFetcher(root).fetch((root / "link.txt").as_uri())


def test_it_pdf_05_render_never_fetches_external_urls() -> None:
    hits: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            hits.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    html = f"""<html><head><link rel="stylesheet" href="{base}/x.css">
      <style>@font-face {{ font-family: X; src: url("{base}/font.ttf"); }}
      body {{ background: url("{base}/bg.png"); font-family: X; }}</style></head>
      <body><img src="{base}/logo.png"><p>Body</p></body></html>"""
    fetcher = RestrictedFetcher()
    try:
        pdf = weasyprint.HTML(
            string=html, base_url=ASSETS_DIR.as_uri() + "/", url_fetcher=fetcher
        ).write_pdf()
    finally:
        server.shutdown()
    assert pdf.startswith(b"%PDF-")
    assert hits == []  # nothing reached the network
    assert {url.rsplit("/", 1)[1] for url in fetcher.refused} >= {
        "x.css",
        "font.ttf",
        "bg.png",
        "logo.png",
    }
