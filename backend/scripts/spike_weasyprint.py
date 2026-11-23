"""M0.4 risk spike A (V-06, V-16): WeasyPrint renders a one-page PDF inside the container,
with the bundled Noto fonts and a visible ₹.

This is verification tooling, not product code: it is excluded from the image and run by
hand against the built image, with networking disabled to prove rendering needs no network:

    docker run --rm --network none \
      -v "$PWD/backend/scripts:/spike:ro" -v "$OUT_DIR:/out" \
      hive-docs:local python /spike/spike_weasyprint.py /out/spike-a.pdf

The production renderer (classic@1 template, restricted URL fetcher, worker pool) is M4.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import weasyprint

FONTS = Path("/app/backend/app/modules/rendering/assets/fonts")
SPECIMEN = "SPECIMEN — demonstration document, not a tax invoice."

HTML = f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<title>M0 spike A</title>
<style>
  @font-face {{ font-family: "Noto Sans"; font-weight: 400; src: url("NotoSans-Regular.ttf"); }}
  @font-face {{ font-family: "Noto Sans"; font-weight: 700; src: url("NotoSans-Bold.ttf"); }}
  @font-face {{ font-family: "Noto Sans Devanagari"; font-weight: 400;
                src: url("NotoSansDevanagari-Regular.ttf"); }}
  @page {{
    size: A4;
    margin: 18mm 16mm 22mm 16mm;
    @bottom-left {{ content: "{SPECIMEN}"; font: 8pt "Noto Sans"; color: #5B6472; }}
    @bottom-right {{ content: "Page " counter(page) " of " counter(pages);
                     font: 8pt "Noto Sans"; color: #5B6472; }}
  }}
  body {{ font-family: "Noto Sans", "Noto Sans Devanagari"; font-size: 9.5pt; color: #1B2A41; }}
  h1 {{ font-size: 18pt; font-weight: 700; }}
  .amount {{ font-feature-settings: "tnum"; font-size: 24pt; font-weight: 700; }}
  td {{ padding: 2pt 8pt 2pt 0; }}
  td.num {{ text-align: right; font-feature-settings: "tnum"; }}
</style>
</head>
<body>
  <h1>WeasyPrint container spike (M0)</h1>
  <p>Grand total: <span class="amount">₹2,700.00</span></p>
  <table>
    <tr><td>Brand identity consultation</td><td class="num">₹1,800.00</td></tr>
    <tr><td>Website support hours</td><td class="num">₹900.00</td></tr>
    <tr><td>Largest allowed total</td><td class="num">₹99,99,99,99,99,999.99</td></tr>
  </table>
  <p>Rupee sign, regular and bold: ₹ <strong>₹</strong></p>
  <p>Devanagari fallback: हिमालय डिज़ाइन स्टूडियो</p>
</body>
</html>
"""


def main(out_path: str) -> int:
    document = weasyprint.HTML(string=HTML, base_url=FONTS.as_uri() + "/").render()
    pdf = document.write_pdf()
    Path(out_path).write_bytes(pdf)
    print(
        json.dumps(
            {
                "weasyprint": weasyprint.__version__,
                "pages": len(document.pages),
                "bytes": len(pdf),
                "header": pdf[:8].decode("latin-1"),
                "sha256": hashlib.sha256(pdf).hexdigest(),
                "fonts_dir_files": sorted(p.name for p in FONTS.iterdir()),
            },
            indent=2,
        )
    )
    return 0 if len(document.pages) == 1 and pdf.startswith(b"%PDF-") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
