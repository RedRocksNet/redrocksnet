#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
IMAGE_DIR = ROOT / "sutra_images"
OUTPUT = ROOT / "sutras.html"
SITE_URL = "https://www.redrocks.net"


def generate_html(images):
    cards = []
    for img in images:
        cards.append(
            f"""
<button class="thumb" type="button" onclick="showLightbox('{html.escape(img)}')">
  <div class="thumb-frame">
    <img src="sutra_images/{html.escape(img)}" alt="佛经手书作品">
  </div>
</button>
""".strip()
        )

    images_json = json.dumps(images, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="RedRocks 佛经手书页面：在一笔一划的重复中，让书写成为安顿内心的一种节律。">
  <link rel="canonical" href="{SITE_URL}/sutras.html">
  <meta property="og:site_name" content="RedRocks">
  <meta property="og:title" content="佛经手书 · RedRocks">
  <meta property="og:description" content="在一笔一划的重复中，让书写成为安顿内心的一种节律。">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{SITE_URL}/sutras.html">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="佛经手书 · RedRocks">
  <meta name="twitter:description" content="在一笔一划的重复中，让书写成为安顿内心的一种节律。">
  <title>佛经手书 · RedRocks</title>
  <link rel="stylesheet" href="/nav.css">

  <style>
    :root {{
      --bg: #171a19;
      --panel: rgba(43, 48, 44, 0.8);
      --panel-strong: rgba(49, 55, 50, 0.9);
      --line: rgba(215, 201, 165, 0.12);
      --text: #ebe5d8;
      --muted: #b9b1a1;
      --accent: #c7a86b;
      --shadow: 0 24px 70px rgba(0, 0, 0, 0.18);
      --serif: "Iowan Old Style", "Palatino Linotype", "URW Palladio L", "Book Antiqua", "Songti SC", "STSong", serif;
      --sans: "Avenir Next", "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", sans-serif;
    }}

    * {{
      box-sizing: border-box;
    }}

    html, body {{
      margin: 0;
      padding: 0;
      min-height: 100%;
    }}

    body {{
      color: var(--text);
      font-family: var(--sans);
      background:
        linear-gradient(180deg, rgba(23, 26, 25, 0.72), rgba(23, 26, 25, 0.92)),
        radial-gradient(circle at top, rgba(111, 138, 114, 0.12), transparent 28%),
        linear-gradient(180deg, #191d1b 0%, #1c211f 32%, #232826 100%);
      letter-spacing: 0.01em;
      background-attachment: fixed;
    }}

    body::before {{
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
    }}

    main {{
      width: min(1100px, calc(100% - 32px));
      margin: 0 auto;
      padding: 96px 0 64px;
    }}

    .hero {{
      position: relative;
      display: grid;
      grid-template-columns: minmax(0, 1.18fr) minmax(260px, 0.82fr);
      gap: 22px;
      padding: 22px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background:
        linear-gradient(135deg, rgba(50, 56, 51, 0.92), rgba(31, 35, 33, 0.88)),
        var(--panel);
      box-shadow: var(--shadow);
      overflow: hidden;
    }}

    .hero::after {{
      content: "";
      position: absolute;
      inset: auto -14% -34% 30%;
      height: 320px;
      background: radial-gradient(circle, rgba(199, 168, 107, 0.12), transparent 70%);
      pointer-events: none;
    }}

    .hero-copy,
    .hero-panel {{
      position: relative;
      z-index: 1;
    }}

    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.24em;
      text-transform: uppercase;
    }}

    .eyebrow::before {{
      content: "";
      width: 30px;
      height: 1px;
      background: rgba(199, 168, 107, 0.5);
    }}

    .hero-title {{
      margin: 14px 0 18px;
      font-family: var(--serif);
      font-size: clamp(34px, 6vw, 64px);
      line-height: 0.98;
      letter-spacing: -0.03em;
    }}

    .hero-title span {{
      display: block;
      color: rgba(244, 239, 227, 0.88);
      font-size: 0.64em;
      font-weight: 400;
      margin-top: 10px;
    }}

    .hero-lead {{
      margin: 0;
      max-width: 38em;
      color: #d8d0c1;
      font-size: 16px;
      line-height: 1.92;
    }}

    .hero-panel {{
      display: grid;
      gap: 16px;
      align-content: start;
    }}

    .panel-card {{
      padding: 20px;
      border-radius: 22px;
      border: 1px solid var(--line);
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0)),
        var(--panel-strong);
    }}

    .panel-label {{
      color: var(--accent);
      font-size: 11px;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      margin-bottom: 12px;
    }}

    .panel-copy {{
      margin: 0;
      color: #d1c9ba;
      font-size: 14px;
      line-height: 1.8;
    }}

    .panel-quote {{
      margin: 0;
      font-family: var(--serif);
      font-size: 24px;
      line-height: 1.35;
      color: #f0e7d7;
    }}

    .gallery-shell {{
      margin-top: 28px;
      padding: 24px;
      border-radius: 26px;
      border: 1px solid var(--line);
      background:
        linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0)),
        var(--panel);
      box-shadow: var(--shadow);
    }}

    .gallery-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
    }}

    .thumb {{
      border: 0;
      padding: 0;
      margin: 0;
      background: rgba(255,255,255,0.03);
      border-radius: 18px;
      overflow: hidden;
      cursor: pointer;
      border: 1px solid rgba(255,255,255,0.06);
      transition: transform 0.22s ease, border-color 0.22s ease;
    }}

    .thumb:hover {{
      transform: translateY(-2px);
      border-color: rgba(215, 201, 165, 0.24);
    }}

    .thumb-frame {{
      width: 100%;
      height: 240px;
      background: #111514;
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    .thumb-frame img {{
      width: 100%;
      height: 100%;
      object-fit: contain;
      display: block;
    }}

    .lightbox {{
      display: none;
      position: fixed;
      z-index: 9999;
      inset: 0;
      background: rgba(0, 0, 0, 0.92);
    }}

    .lightbox img {{
      display: block;
      max-width: 92vw;
      max-height: 88vh;
      margin: 5vh auto 0;
      object-fit: contain;
    }}

    .close {{
      position: absolute;
      top: 18px;
      right: 28px;
      color: white;
      font-size: 38px;
      line-height: 1;
      cursor: pointer;
    }}

    @media (max-width: 900px) {{
      .hero {{
        grid-template-columns: 1fr;
      }}
    }}

    @media (max-width: 640px) {{
      main {{
        width: min(100%, calc(100% - 20px));
        padding-top: 88px;
      }}

      .hero,
      .gallery-shell {{
        padding: 18px;
        border-radius: 22px;
      }}

      .hero-title {{
        font-size: 34px;
      }}

      .hero-lead {{
        font-size: 15px;
        line-height: 1.88;
      }}

      .thumb-frame {{
        height: 210px;
      }}
    }}
  </style>
</head>
<body>
  <div id="rr-nav-mount" data-current="sutras"></div>

  <main>
    <section class="hero">
      <div class="hero-copy">
        <div class="eyebrow">Sutras</div>
        <h1 class="hero-title">佛经手书<span>在一笔一划的重复中，让内心慢慢安定</span></h1>
        <p class="hero-lead">佛经书写最初并不是源于系统的佛学认识，而是来自一次非常具体的生命情境。后来，写经成了我生活中不可或缺的一部分，也让我在书写里慢慢体会到专注、安静、修行与放下。</p>
      </div>

      <div class="hero-panel">
        <div class="panel-card">
          <div class="panel-label">Practice</div>
          <p class="panel-copy">静的时候可以写，焦躁的时候更该写。写到最后，重要的也许不再是“懂了多少”，而是回到那种一个字一个字写下去的简单。</p>
        </div>
        <div class="panel-card">
          <div class="panel-label">一句话</div>
          <p class="panel-quote">不是展示字，而是借书写安顿自己。</p>
        </div>
      </div>
    </section>

    <section class="gallery-shell">
      <div class="gallery-grid">
        {"".join(cards)}
      </div>
    </section>
  </main>

  <div class="lightbox" id="lightbox" onclick="hideLightbox()">
    <span class="close" aria-hidden="true">&times;</span>
    <img id="lightbox-img" src="" alt="佛经手书放大图">
  </div>

  <script>
    const images = {images_json};
    let currentIndex = -1;

    function showLightbox(name) {{
      const lb = document.getElementById('lightbox');
      const lbImg = document.getElementById('lightbox-img');
      lb.style.display = 'block';
      lbImg.src = 'sutra_images/' + name;
      currentIndex = images.indexOf(name);
    }}

    function hideLightbox() {{
      document.getElementById('lightbox').style.display = 'none';
    }}

    document.addEventListener('keydown', function(e) {{
      const lb = document.getElementById('lightbox');
      const lbImg = document.getElementById('lightbox-img');
      if (lb.style.display !== 'block') return;

      if (e.key === 'ArrowRight') {{
        currentIndex = (currentIndex + 1) % images.length;
        lbImg.src = 'sutra_images/' + images[currentIndex];
      }} else if (e.key === 'ArrowLeft') {{
        currentIndex = (currentIndex - 1 + images.length) % images.length;
        lbImg.src = 'sutra_images/' + images[currentIndex];
      }} else if (e.key === ' ' || e.key === 'Escape') {{
        hideLightbox();
      }}
    }});
  </script>

  <script src="/nav.js" defer></script>
</body>
</html>"""


if __name__ == "__main__":
    images = sorted(
        f.name
        for f in IMAGE_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    )
    OUTPUT.write_text(generate_html(images), encoding="utf-8")
    print("✅ sutras.html 已生成")
