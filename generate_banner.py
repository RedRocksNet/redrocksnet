#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
BANNER_DIR = ROOT / "banner"
OUTPUT_JS = ROOT / "banner_list.js"

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def main():
    if not BANNER_DIR.exists() or not BANNER_DIR.is_dir():
        # Still generate a valid JS file so index.html won't crash
        OUTPUT_JS.write_text("window.__RR_BANNERS__ = [];\n", encoding="utf-8")
        print(f"⚠️ banner/ folder not found: {BANNER_DIR}")
        print("✅ Generated empty banner_list.js")
        return

    files = [
        p for p in BANNER_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMG_EXTS and not p.name.startswith(".")
    ]

    # stable order (useful for reproducibility)
    files.sort(key=lambda p: p.name.lower())

    # website paths (served from root)
    paths = [f"/banner/{p.name}" for p in files]

    # Write a simple global array for index.html to use
    js = "window.__RR_BANNERS__ = " + json.dumps(paths, ensure_ascii=False) + ";\n"
    OUTPUT_JS.write_text(js, encoding="utf-8")

    print(f"✅ Generated {OUTPUT_JS.name} with {len(paths)} banner(s).")
    if len(paths) == 0:
        print("⚠️ banner/ exists but contains no supported images.")


if __name__ == "__main__":
    main()