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
    :root {
      --bg: #171a19;
      --panel: rgba(43, 48, 44, 0.8);
      --panel-strong: rgba(49, 55, 50, 0.9);
      --line: rgba(215, 201, 165, 0.12);
      --line-strong: rgba(215, 201, 165, 0.22);
      --text: #ebe5d8;
      --muted: #b9b1a1;
      --accent: #c7a86b;
      --shadow: 0 24px 70px rgba(0, 0, 0, 0.18);
      --serif: "Iowan Old Style", "Palatino Linotype", "URW Palladio L", "Book Antiqua", "Songti SC", "STSong", serif;
      --sans: "Avenir Next", "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", sans-serif;
    }

    * {
      box-sizing: border-box;
    }

    html, body {
      margin: 0;
      padding: 0;
      min-height: 100%;
    }

    body {
      color: var(--text);
      font-family: var(--sans);
      background:
        linear-gradient(180deg, rgba(23, 26, 25, 0.72), rgba(23, 26, 25, 0.92)),
        radial-gradient(circle at top, rgba(111, 138, 114, 0.12), transparent 28%),
        linear-gradient(180deg, #191d1b 0%, #1c211f 32%, #232826 100%);
      letter-spacing: 0.01em;
      background-attachment: fixed;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(255, 255, 255, 0.014) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.012) 1px, transparent 1px);
      background-size: 100% 34px, 34px 100%;
      mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.34), transparent 78%);
      opacity: 0.18;
    }

    main {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 96px 0 64px;
      box-sizing: border-box;
    }

    h1 {
      margin: 0 0 8px;
      font-family: var(--serif);
      font-size: clamp(28px, 4.8vw, 48px);
      line-height: 1.02;
      letter-spacing: -0.03em;
    }

    .subtle {
      color: var(--muted);
      font-size: 15px;
      line-height: 1.8;
    }

    .hero {
      position: relative;
      display: grid;
      grid-template-columns: minmax(0, 1.24fr) minmax(240px, 0.76fr);
      gap: 18px;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background:
        linear-gradient(135deg, rgba(50, 56, 51, 0.92), rgba(31, 35, 33, 0.88)),
        var(--panel);
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .hero::after {
      content: "";
      position: absolute;
      inset: auto -14% -34% 30%;
      height: 320px;
      background: radial-gradient(circle, rgba(199, 168, 107, 0.12), transparent 70%);
      pointer-events: none;
    }

    .hero-copy,
    .hero-panel {
      position: relative;
      z-index: 1;
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.24em;
      text-transform: uppercase;
      margin-bottom: 14px;
    }

    .eyebrow::before {
      content: "";
      width: 30px;
      height: 1px;
      background: rgba(199, 168, 107, 0.5);
    }

    .hero-title span {
      display: block;
      color: rgba(244, 239, 227, 0.88);
      font-size: 0.58em;
      font-weight: 400;
      margin-top: 8px;
      letter-spacing: 0;
    }

    .hero-lead {
      margin: 0;
      max-width: 34em;
      color: #d8d0c1;
      font-size: 15px;
      line-height: 1.8;
    }

    .hero-panel {
      display: grid;
      gap: 16px;
      align-content: start;
    }

    .panel-card {
      padding: 16px;
      border-radius: 18px;
      border: 1px solid var(--line);
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0)),
        var(--panel-strong);
    }

    .panel-label {
      color: var(--accent);
      font-size: 11px;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      margin-bottom: 12px;
    }

    .panel-copy {
      margin: 0;
      color: #d1c9ba;
      font-size: 13px;
      line-height: 1.7;
    }

    .panel-quote {
      margin: 0;
      font-family: var(--serif);
      font-size: 20px;
      line-height: 1.35;
      color: #f0e7d7;
    }

    .section {
      margin-top: 28px;
      padding: 28px;
      border-radius: 26px;
      border: 1px solid var(--line);
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0)),
        rgba(40, 45, 42, 0.76);
      box-shadow: var(--shadow);
    }

    .section-head {
      margin-bottom: 22px;
    }

    .section-kicker {
      color: var(--accent);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.22em;
      margin-bottom: 10px;
    }

    .section-title {
      margin: 0;
      font-family: var(--serif);
      font-size: clamp(28px, 3.4vw, 42px);
      line-height: 1.05;
      letter-spacing: -0.025em;
      text-wrap: balance;
    }

    /* ===== Series grid (index) ===== */
    .series-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }

    .series-card {
      background:
        radial-gradient(circle at top right, rgba(199, 168, 107, 0.1), transparent 35%),
        linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0)),
        rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.07);
      border-radius: 22px;
      overflow: hidden;
      text-decoration: none;
      color: inherit;
      transition: transform 0.24s ease, border-color 0.24s ease, background 0.24s ease;
    }

    .series-card:hover {
      transform: translateY(-4px);
      border-color: rgba(217, 202, 162, 0.28);
      background:
        radial-gradient(circle at top right, rgba(199, 168, 107, 0.14), transparent 38%),
        linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0)),
        rgba(255,255,255,0.055);
    }

    /* cover frame keeps consistent grid height,
       but image keeps original aspect ratio (no crop) */
    .series-cover {
      width: 100%;
      height: 260px;
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
      padding: 18px 18px 20px;
    }

    .series-title {
      font-family: var(--serif);
      font-size: 30px;
      line-height: 1.08;
      margin: 0 0 8px;
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
      border-radius: 18px;
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
      height: 260px;
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
      color: var(--muted);
      text-decoration: none;
    }

    .backlink a:hover {
      color: var(--text);
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
      color: var(--muted);
      font-size: 13px;
    }

    @media (max-width: 980px) {
      .hero,
      .series-grid {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 720px) {
      main {
        width: min(100% - 20px, 1180px);
        padding-top: 82px;
        padding-bottom: 42px;
      }

      .hero,
      .section {
        padding: 18px;
        border-radius: 22px;
      }

      .hero-title {
        font-size: clamp(34px, 11vw, 54px);
      }

      .series-cover,
      .thumb-frame {
        height: 220px;
      }
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
<section class="hero">
  <div class="hero-copy">
    <div class="eyebrow">Gallery</div>
    <h1 class="hero-title">摄影作品<span>从几种不同的观看方式进入</span></h1>
    <p class="hero-lead">这里的系列不是按题材堆放，而是按观看世界的方式重新组织。</p>
  </div>

  <div class="hero-panel">
    <div class="panel-card">
      <div class="panel-label">Current Axis</div>
      <p class="panel-copy">静观、行走、人间、微光与黑白，不是分类，而是几种不同的目光。</p>
      <p class="panel-quote" style="margin-top: 14px;">让图像先说话。</p>
    </div>
  </div>
</section>

<section class="section">
  <div class="section-head">
    <div class="section-kicker">Series</div>
    <h2 class="section-title">从几种不同的观看方式进入。</h2>
  </div>
  <div class="series-grid">
    {''.join(cards)}
  </div>
</section>
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
<section class="hero">
  <div class="hero-copy">
    <div class="eyebrow">Series</div>
    <h1 class="hero-title">{html.escape(name)}<span>{html.escape(motto)}</span></h1>
    <p class="hero-lead">这一组照片不是在说明一个题材，而是在保留一种观看时的内在状态。慢一点看，画面之外的气息会更清楚。</p>
  </div>

  <div class="hero-panel">
    <div class="panel-card">
      <div class="panel-label">Back</div>
      <p class="panel-copy"><a href="gallery.html">← 返回系列目录</a></p>
    </div>
  </div>
</section>

<section class="section">
  <div class="section-head">
    <div class="section-kicker">Frames</div>
    <h2 class="section-title">点击放大，继续观看。</h2>
  </div>
  <div class="thumb-grid">
    {''.join(thumbs)}
  </div>
</section>

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
