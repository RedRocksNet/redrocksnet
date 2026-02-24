#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import html
from pathlib import Path
from datetime import datetime

try:
    import markdown  # pip3 install markdown
except ImportError:
    print("ERROR: Missing dependency 'markdown'. Install with: pip3 install markdown")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
ARTICLES_DIR = ROOT / "articles"          # input: .md ; output: .html (in same folder)
INDEX_OUT = ROOT / "articles.html"        # output index page at root
SITE_TITLE = "RedRocks"


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def extract_title(md_text: str, fallback: str) -> str:
    # First H1: "# Title"
    for line in md_text.splitlines():
        m = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
        if line.strip():
            break
    return fallback.strip()


def fmt_date(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def base_css() -> str:
    # Minimal page styling; nav styling is provided by /nav.css
    return """
:root{
  --bg:#0b0b0b; --fg:#f2f2f2; --muted:#b8b8b8; --card:#121212; --line:#1f1f1f;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  background:var(--bg); color:var(--fg); line-height:1.7;
}
a{color:var(--fg); text-decoration:none}
a:hover{text-decoration:underline}

main{max-width:980px; margin:0 auto; padding:92px 18px 56px} /* leave space for fixed nav */
h1{font-size:34px; margin:12px 0 10px; line-height:1.25}
.subtle{color:var(--muted); font-size:14px}

.footer{
  margin-top:40px; padding-top:18px; border-top:1px solid rgba(255,255,255,.08);
  color:var(--muted); font-size:13px;
}

/* index list */
.list-wrap{
  margin-top:18px;
  background:var(--card);
  border:1px solid rgba(255,255,255,.06);
  border-radius:14px;
  overflow:hidden;
}
.list-head{
  display:flex; justify-content:space-between; align-items:center;
  padding:14px 16px; border-bottom:1px solid rgba(255,255,255,.06);
}
.list{
  max-height: 66vh;
  overflow-y:auto;
}
.item{
  display:flex; gap:12px; align-items:baseline; justify-content:space-between;
  padding:14px 16px;
  border-bottom:1px solid rgba(255,255,255,.05);
}
.item:last-child{border-bottom:none}
.item .title{font-size:16px}
.item .date{color:var(--muted); font-size:13px; white-space:nowrap}

/* article content */
.article pre{
  background:#111; border:1px solid rgba(255,255,255,.08);
  padding:14px; border-radius:12px; overflow:auto;
}
.article code{font-family: ui-monospace,SFMono-Regular,Menlo,Monaco,"Cascadia Mono","Segoe UI Mono",Consolas,monospace}
.article blockquote{
  margin:14px 0; padding:10px 14px; border-left:3px solid rgba(255,255,255,.18);
  color:var(--muted); background:rgba(255,255,255,.03); border-radius:10px;
}
.article img{max-width:100%; height:auto; border-radius:12px; border:1px solid rgba(255,255,255,.06)}
"""


def wrap_page(page_title: str, current_key: str, body_html: str) -> str:
    # Nav module mount + assets
    # current_key: home/gallery/sutras/articles/about
    safe_title = html.escape(page_title)
    year = datetime.now().year
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{safe_title} · {SITE_TITLE}</title>
  <link rel="stylesheet" href="/nav.css">
  <style>{base_css()}</style>
</head>
<body>
  <div id="rr-nav-mount" data-current="{html.escape(current_key)}"></div>

  <main>
    {body_html}
    <div class="footer">© {year} {SITE_TITLE}</div>
  </main>

  <script src="/nav.js" defer></script>
</body>
</html>
"""


def render_markdown(md_text: str) -> str:
    return markdown.markdown(
        md_text,
        extensions=["extra", "tables", "fenced_code", "codehilite", "toc"],
        output_format="html5",
    )


def main():
    if not ARTICLES_DIR.exists():
        print(f"ERROR: folder not found: {ARTICLES_DIR}")
        sys.exit(1)

    md_files = sorted(
        [p for p in ARTICLES_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".md"],
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    items = []

    for md_path in md_files:
        md_text = read_text(md_path)
        stem = md_path.stem
        title = extract_title(md_text, fallback=stem)
        mtime = md_path.stat().st_mtime
        date_str = fmt_date(mtime)

        # detail page output: /articles/<stem>.html
        out_path = ARTICLES_DIR / f"{stem}.html"
        content_html = render_markdown(md_text)

        detail_body = f"""
<article class="article">
  <h1>{html.escape(title)}</h1>
  <div class="subtle">{html.escape(date_str)}</div>
  <div style="height:14px"></div>
  {content_html}
</article>
"""
        write_text(out_path, wrap_page(title, "articles", detail_body))

        items.append({
            "title": title,
            "date": date_str,
            "href": f"/articles/{stem}.html",
        })

    # index page: /articles.html
    if items:
        rows = "\n".join(
            f"""<div class="item">
  <div class="title"><a href="{html.escape(it['href'])}">{html.escape(it['title'])}</a></div>
  <div class="date">{html.escape(it['date'])}</div>
</div>"""
            for it in items
        )

        index_body = f"""
<h1>随笔</h1>
<div class="subtle">按最近发布顺序排列</div>

<div class="list-wrap">
  <div class="list-head">
    <div>文章目录</div>
    <div class="subtle">{len(items)} 篇</div>
  </div>
  <div class="list">
    {rows}
  </div>
</div>
"""
    else:
        index_body = """
<h1>随笔</h1>
<div class="subtle">暂无文章。请在 <code>./articles/</code> 中放入 Markdown 文件（.md），然后执行生成。</div>
"""

    write_text(INDEX_OUT, wrap_page("随笔", "articles", index_body))

    print(f"✅ articles.html 已生成：{INDEX_OUT}")
    print(f"✅ 文章页已生成：{len(items)} 篇（位于 {ARTICLES_DIR}/ ）")


if __name__ == "__main__":
    main()