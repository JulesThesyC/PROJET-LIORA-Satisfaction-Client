#!/usr/bin/env python
"""Exporte docs/rapport_global.md en PDF via Playwright (HTML stylé)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "docs" / "rapport_global.md"
PDF_PATH = ROOT / "docs" / "rapport_global.pdf"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8"/>
  <title>Rapport global — Projet LIORA</title>
  <style>
    @page {{ size: A4; margin: 2cm; }}
    body {{
      font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
      font-size: 11pt;
      line-height: 1.5;
      color: #1a1a1a;
      max-width: 100%;
    }}
    h1 {{ color: #0d47a1; border-bottom: 2px solid #58a6ff; padding-bottom: 8px; page-break-before: always; }}
    h1:first-of-type {{ page-break-before: avoid; }}
    h2 {{ color: #1565c0; margin-top: 1.4em; }}
    h3 {{ color: #1976d2; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 10pt; }}
    th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: left; }}
    th {{ background: #e3f2fd; }}
    code {{ background: #f5f5f5; padding: 2px 5px; border-radius: 3px; font-size: 9pt; }}
    pre {{ background: #f5f5f5; padding: 12px; overflow-x: auto; font-size: 9pt; border-left: 4px solid #58a6ff; }}
    blockquote {{ border-left: 4px solid #90caf9; margin-left: 0; padding-left: 1em; color: #444; }}
    a {{ color: #1565c0; }}
    hr {{ border: none; border-top: 1px solid #ddd; margin: 2em 0; }}
    .cover {{
      text-align: center;
      padding: 3cm 1cm;
      page-break-after: always;
    }}
    .cover h1 {{ border: none; font-size: 28pt; page-break-before: avoid; }}
    .cover p {{ font-size: 12pt; color: #555; }}
  </style>
</head>
<body>
<div class="cover">
  <h1>Projet LIORA</h1>
  <p><strong>Satisfaction client &amp; Supply Chain</strong></p>
  <p>Rapport global — Data Engineering</p>
  <p>JulesThesyC · Mai 2026</p>
  <p><em>Trustpilot France — Amazon, Chronopost, Tesla, Temu</em></p>
</div>
{body}
</body>
</html>
"""


def main() -> None:
    try:
        import markdown
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown", "-q"])
        import markdown

    from playwright.sync_api import sync_playwright

    md_text = MD_PATH.read_text(encoding="utf-8")
    body_html = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "nl2br"],
    )
    full_html = HTML_TEMPLATE.format(body=body_html)

    html_tmp = ROOT / "docs" / "_rapport_export.html"
    html_tmp.write_text(full_html, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(html_tmp.as_uri(), wait_until="networkidle")
        page.pdf(
            path=str(PDF_PATH),
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
        )
        browser.close()

    html_tmp.unlink(missing_ok=True)
    print(f"PDF généré : {PDF_PATH}")


if __name__ == "__main__":
    main()
