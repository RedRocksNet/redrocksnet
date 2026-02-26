#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IMAGES_ROOT = ROOT / "images"
OUTPUT_INDEX = ROOT / "gallery.html"

SITE_TITLE = "RedRocks"

SERIES = [
    ("stillness", "静观", "世界不要求回应，只要求被看见。"),
    ("walking",   "行走", "身体在路上，心在当下。"),
    ("human",     "人间", "世界不是风景，是众生。"),
    ("light",     "微光", "光不是照亮世界，而是照见自己。"),
    ("bw",        "黑白", "从三维世界到二维画面，从色彩缤纷到黑白灰，观察即抽象。"),
]

IMG_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
COVER_CANDIDATES = ("cover.jpg", "cover.jpeg", "cover.png", "cover.webp", "cover.gif")


def list_images(folder: Path):
    if not folder.exists() or not folder.is_dir():
        return []
    imgs = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS]
    imgs.sort(key=lambda p: p.name.lower())
    return imgs


def pick_cover(folder: str):
    series_dir = IMAGES_ROOT / folder
    for name in COVER_CANDIDATES:
        p = series_dir / name
        if p.exists() and p.is_file():
            return f"images/{folder}/{p.name}"

    imgs = list_images(series_dir)
    if imgs:
        return f"images/{folder}/{imgs[0].name}"
    return ""


def base_head(title: str) -> str:
    safe_title = html.escape(title)
    head = """<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>__TITLE__</title>
  <link rel="stylesheet" href="/nav.css">
  <style>
    body {
      background-color: #111;
      color: white;
      font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "Segoe UI",
        Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
      margin: 0;
      padding: 0;
    }

    main {
      max-width: 1100px;
      margin: 0 auto;
      padding: 92px 18px 56px; /* space for fixed nav */
      box-sizing: border-box;
    }

    h1 {
      margin: 12px 0 10px;
      font-size: 34px;
      letter-spacing: 1px;
    }

    .subtle {
      color: #b8b8b8;
      font-size: 14px;
      line-height: 1.6;
    }

    /* ===== Series grid (index) ===== */
    .series-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
      margin-top: 18px;
    }

    .series-card {
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 14px;
      overflow: hidden;
      text-decoration: none;
      color: inherit;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .series-card:hover {
      transform: translateY(-2px);
      border-color: rgba(255,255,255,0.18);
    }

    /* cover frame keeps consistent grid height,
       but image keeps original aspect ratio (no crop) */
    .series-cover {
      width: 100%;
      height: 180px;
      background: #0b0b0b;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .series-cover img {
      width: 100%;
      height: 100%;
      object-fit: contain;
      display: block;
    }

    .series-meta {
      padding: 12px 14px 14px;
    }

    .series-title {
      font-size: 18px;
      margin: 0 0 6px;
    }

    /* ===== Thumbnails (series page) ===== */
    .thumb-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 14px;
      margin-top: 18px;
    }

    .thumb {
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 12px;
      overflow: hidden;
      cursor: pointer;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .thumb:hover {
      transform: translateY(-1px);
      border-color: rgba(255,255,255,0.18);
    }

    .thumb-frame {
      width: 100%;
      height: 220px;  /* uniform grid */
      background: #0b0b0b;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .thumb-frame img {
      width: 100%;
      height: 100%;
      object-fit: contain; /* keep aspect ratio */
      display: block;
    }

    .backlink {
      margin-top: 18px;
    }

    .backlink a {
      color: #b8b8b8;
      text-decoration: none;
    }

    .backlink a:hover {
      color: #fff;
      text-decoration: underline;
    }

    /* ===== Lightbox ===== */
    #lightbox {
      display: none;
      position: fixed;
      z-index: 9999;
      padding-top: 60px;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background-color: rgba(0,0,0,0.92);
      box-sizing: border-box;
    }

    #lightbox #lightbox-img {
      display: block;
      margin: 0 auto;
      max-width: 92vw;
      max-height: 88vh;
      width: auto;
      height: auto;
      object-fit: contain;
    }

    #lightbox .close {
      position: absolute;
      top: 20px;
      right: 35px;
      color: white;
      font-size: 40px;
      font-weight: bold;
      cursor: pointer;
    }

    #lightbox .nav-btn {
      position: absolute;
      top: 50%;
      font-size: 60px;
      color: white;
      cursor: pointer;
      user-select: none;
      padding: 10px;
      transform: translateY(-50%);
    }

    #lightbox .prev { left: 20px; }
    #lightbox .next { right: 20px; }

    .footer {
      margin-top: 40px;
      padding-top: 18px;
      border-top: 1px solid rgba(255,255,255,0.08);
      color: #b8b8b8;
      font-size: 13px;
    }
  </style>
</head>"""
    return head.replace("__TITLE__", safe_title)


def page_wrap(title: str, current: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh">
{base_head(title)}
<body>
  <div id="rr-nav-mount" data-current="{html.escape(current)}"></div>
  <main>
    {body_html}
    <div class="footer">© {SITE_TITLE}</div>
  </main>
  <script src="/nav.js" defer></script>
</body>
</html>"""


def build_index() -> str:
    cards = []
    for folder, name, motto in SERIES:
        imgs = list_images(IMAGES_ROOT / folder)
        href = f"gallery-{folder}.html"

        cover_src = pick_cover(folder)
        if cover_src:
            cover_html = f'<div class="series-cover"><img src="{html.escape(cover_src)}" alt="cover"></div>'
        else:
            cover_html = '<div class="series-cover"></div>'

        cards.append(f"""
<a class="series-card" href="{html.escape(href)}">
  {cover_html}
  <div class="series-meta">
    <div class="series-title">{html.escape(name)}</div>
    <div class="subtle">{html.escape(motto)}</div>
    <div class="subtle" style="margin-top:8px;">{len(imgs)} 张</div>
  </div>
</a>
""".strip())

    body = f"""
<h1>摄影作品</h1>
<div class="subtle">按观看方式分为若干系列。点击进入。</div>

<div class="series-grid">
  {''.join(cards)}
</div>
""".strip()

    return page_wrap("摄影作品", "gallery", body)


def build_series_page(folder: str, name: str, motto: str) -> str:
    imgs = list_images(IMAGES_ROOT / folder)

    thumbs = []
    for p in imgs:
        src = f"images/{folder}/{p.name}"
        thumbs.append(f"""
<div class="thumb" onclick="openLightbox('{html.escape(src)}')">
  <div class="thumb-frame">
    <img src="{html.escape(src)}" alt="">
  </div>
</div>
""".strip())

    image_paths = [f"images/{folder}/{p.name}" for p in imgs]
    js_array = json.dumps(image_paths, ensure_ascii=False)

    body = f"""
<h1>{html.escape(name)}</h1>
<div class="subtle">{html.escape(motto)}</div>

<div class="backlink"><a href="gallery.html">← 返回系列目录</a></div>

<div class="thumb-grid">
  {''.join(thumbs)}
</div>

<div id="lightbox">
  <span class="close" onclick="closeLightbox()">&times;</span>
  <span class="nav-btn prev" onclick="changeImage(-1)">&#10094;</span>
  <img id="lightbox-img" src="">
  <span class="nav-btn next" onclick="changeImage(1)">&#10095;</span>
</div>

<script>
  let images = {js_array};
  let currentIndex = 0;

  function openLightbox(src) {{
    currentIndex = images.indexOf(src);
    document.getElementById('lightbox').style.display = "block";
    document.getElementById('lightbox-img').src = src;
  }}

  function closeLightbox() {{
    document.getElementById('lightbox').style.display = "none";
  }}

  function changeImage(direction) {{
    if (!images.length) return;
    currentIndex = (currentIndex + direction + images.length) % images.length;
    document.getElementById('lightbox-img').src = images[currentIndex];
  }}

  document.addEventListener('keydown', function(e) {{
    const lb = document.getElementById('lightbox');
    if (lb.style.display !== 'block') return;

    if (e.key === 'ArrowRight') {{
      changeImage(1);
    }} else if (e.key === 'ArrowLeft') {{
      changeImage(-1);
    }} else if (e.key === ' ' || e.key === 'Escape') {{
      closeLightbox();
    }}
  }});
</script>
""".strip()

    return page_wrap(f"{name} · 摄影作品", "gallery", body)


def main():
    OUTPUT_INDEX.write_text(build_index(), encoding="utf-8")

    for folder, name, motto in SERIES:
        out = ROOT / f"gallery-{folder}.html"
        out.write_text(build_series_page(folder, name, motto), encoding="utf-8")

    print("✅ Gallery series pages generated:")
    print(" - gallery.html")
    for folder, _, _ in SERIES:
        print(f" - gallery-{folder}.html")


if __name__ == "__main__":
    main()