#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
SITE_URL = "https://www.redrocks.net"
OUT = ROOT / "sitemap.xml"


def page_url(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return f"{SITE_URL}/"
    return f"{SITE_URL}/{rel}"


def lastmod(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d")


def should_include(path: Path) -> bool:
    if path.suffix.lower() != ".html":
        return False
    if any(part.startswith(".") for part in path.parts):
        return False
    return True


def main() -> None:
    html_files = sorted(p for p in ROOT.rglob("*.html") if should_include(p))
    items = []
    for path in html_files:
        items.append(
            "  <url>\n"
            f"    <loc>{page_url(path)}</loc>\n"
            f"    <lastmod>{lastmod(path)}</lastmod>\n"
            "  </url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(items)
        + "\n</urlset>\n"
    )
    OUT.write_text(xml, encoding="utf-8")
    print(f"✅ sitemap.xml generated with {len(items)} URL(s).")


if __name__ == "__main__":
    main()
