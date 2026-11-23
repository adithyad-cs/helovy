# Self-hosted UI fonts (docs/08 §3; V-16)

Served from the same origin as the SPA (CSP `font-src 'self'`); no font CDN is ever requested.
Both families are licensed under the SIL Open Font License 1.1 (licence texts alongside).

| File | Family / weight | Version | Source | SHA-256 |
| --- | --- | --- | --- | --- |
| `InterVariable.woff2` | Inter (variable, 100–900) | 4.001 | `rsms/inter` → `docs/font-files/InterVariable.woff2` | `693b77d4f32ee9b8bfc995589b5fad5e99adf2832738661f5402f9978429a8e3` |
| `Inter-LICENSE.txt` | Licence for Inter | OFL 1.1 | `rsms/inter` → `LICENSE.txt` | `262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a` |
| `SourceSerif4-Semibold.otf.woff2` | Source Serif 4 Semibold (600) | 4.005 | `adobe-fonts/source-serif` (release branch) → `WOFF2/OTF/` | `7eff2d2fde32c42992e723eb24dcc6dc5b640ef0da97ce373cd38e0604202e30` |
| `SourceSerif4-LICENSE.md` | Licence for Source Serif 4 | OFL 1.1 | `adobe-fonts/source-serif` (release branch) → `LICENSE.md` | `c21d7293d87b6d7ab1d0229a2f55b77f33a7613a6a4e66f6693d68d7d8d09464` |

Downloaded on 23 November 2026 from the official repositories. Source Serif 4 is used at
weight 600 only (landing display and page titles, docs/08 §3).
