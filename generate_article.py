#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import html
import urllib.parse
from pathlib import Path
from datetime import datetime

try:
    import markdown  # pip3 install markdown
except ImportError:
    print("ERROR: Missing dependency 'markdown'. Install with: pip3 install markdown")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
ARTICLES_DIR = ROOT / "articles"          # articles/<category>/*.md
INDEX_OUT = ROOT / "articles.html"        # 随笔首页（栏目卡片）
SITE_TITLE = "RedRocks"
SITE_URL = "https://www.redrocks.net"

IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
COVER_CANDIDATES = ("cover.jpg", "cover.jpeg", "cover.png", "cover.webp", "cover.gif")


# 分类显示名（子目录名大小写不敏感）
CATEGORY_ZH_EN = {
    "photography": "摄影（Photography）",
    "buddhism": "佛法（Buddhism）",
    "misc": "杂文（Misc）",
    "travel": "旅行（Travel）",
    "tap": "TAP宇宙观（TAP）",
}


def category_display_name(dirname: str) -> str:
    """把随笔子目录名转换为要显示的‘中文（English）’。未知目录则原样返回。"""
    key = (dirname or "").strip().lower()
    return CATEGORY_ZH_EN.get(key, dirname)


def category_slug(dirname: str) -> str:
    """Normalize category page filenames/URLs so links stay stable on case-sensitive hosts."""
    return (dirname or "").strip().lower()


def _resolve_case_path(base_dir: Path, rel_path: str) -> Path | None:
    """
    在大小写敏感的环境下（GitHub Pages/Linux）避免 404：
    给定 base_dir + rel_path（可能大小写写错），逐级做 case-insensitive 匹配，
    返回真实存在的 Path；找不到则返回 None。
    """
    try:
        rel = Path(rel_path)
    except Exception:
        return None

    cur = base_dir
    for part in rel.parts:
        if part in (".", ""):
            continue
        if part == "..":
            cur = cur.parent
            continue
        if not cur.exists() or not cur.is_dir():
            return None
        # 精确命中
        cand = cur / part
        if cand.exists():
            cur = cand
            continue
        # 忽略大小写匹配
        target = part.lower()
        found = None
        try:
            for child in cur.iterdir():
                if child.name.lower() == target:
                    found = child
                    break
        except Exception:
            return None
        if found is None:
            return None
        cur = found

    return cur if cur.exists() else None


def fix_resource_url_case(url: str, md_dir: Path) -> str:
    """
    修正 Markdown 生成 HTML 中的本地资源链接（img/src、a/href等）的大小写：
    - 绝对路径 /xxx 从 ROOT 下解析
    - 相对路径 xxx/yyy 从 md_dir 解析
    - 保留 query / fragment
    - 非本地链接（http/mailto/data/#）保持不变
    """
    if not url:
        return url

    u = url.strip()
    lowered = u.lower()
    if lowered.startswith(("http://", "https://", "mailto:", "tel:", "data:")) or u.startswith("#"):
        return url

    parsed = urllib.parse.urlsplit(u)
    path_part = parsed.path

    if not path_part:
        return url

    # 选择解析基准
    if path_part.startswith("/"):
        base = ROOT
        rel = path_part.lstrip("/")
        resolved = _resolve_case_path(base, rel)
        if resolved is None:
            return url
        new_path = "/" + resolved.relative_to(ROOT).as_posix()
    else:
        base = md_dir
        rel = path_part
        resolved = _resolve_case_path(base, rel)
        if resolved is None:
            return url
        new_path = resolved.relative_to(md_dir).as_posix()

    rebuilt = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, new_path, parsed.query, parsed.fragment))
    return rebuilt


def fix_html_resource_cases(html_text: str, md_dir: Path) -> str:
    """
    扫描 HTML 中常见的资源属性（src/href/poster），把其中的本地路径修正为真实大小写。
    """
    def _repl(m: re.Match) -> str:
        attr = m.group(1)
        quote = m.group(2)
        val = m.group(3)
        fixed = fix_resource_url_case(val, md_dir)
        return f'{attr}={quote}{html.escape(fixed, quote=True)}{quote}'

    # 允许单/双引号
    pattern = re.compile(r'\b(src|href|poster)=(["\'])([^"\']+)\2', flags=re.I)
    return pattern.sub(_repl, html_text)

# -------------------------
# Utils
# -------------------------
def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def fmt_date(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def extract_title(md_text: str, fallback: str) -> str:
    """Use first H1 as title; otherwise fallback to filename stem."""
    for line in md_text.splitlines():
        m = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
        if line.strip():
            break
    return fallback.strip()


def strip_first_h1(md_text: str) -> str:
    """Remove first '# ' heading to avoid duplicate title in detail page."""
    lines = md_text.splitlines()
    out = []
    removed = False
    for line in lines:
        if not removed and line.lstrip().startswith("# "):
            removed = True
            continue
        out.append(line)
    return "\n".join(out)


def md_to_plain(md_text: str) -> str:
    """Rough markdown → plain text for excerpt."""
    s = md_text
    # remove code blocks
    s = re.sub(r"```.*?```", " ", s, flags=re.S)
    s = re.sub(r"`[^`]+`", " ", s)
    # remove images/links
    s = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", s)
    s = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", s)
    # remove headings / blockquotes / list markers
    s = re.sub(r"^\s{0,3}#{1,6}\s+", "", s, flags=re.M)
    s = re.sub(r"^\s*>\s?", "", s, flags=re.M)
    s = re.sub(r"^\s*[-*+]\s+", "", s, flags=re.M)
    s = re.sub(r"^\s*\d+\.\s+", "", s, flags=re.M)
    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def excerpt_from_md(md_text: str, max_len: int = 140) -> str:
    plain = md_to_plain(md_text)
    if not plain:
        return ""
    if len(plain) <= max_len:
        return plain
    return plain[: max_len - 1].rstrip() + "…"


def absolute_url(path: str) -> str:
    clean = "/" + (path or "").lstrip("/")
    return f"{SITE_URL}{clean}"


def seo_description(text: str, fallback: str = "") -> str:
    base = re.sub(r"\s+", " ", (text or "").strip())
    if not base:
        base = fallback.strip()
    if len(base) <= 160:
        return base
    return base[:159].rstrip() + "…"


def discover_categories() -> list[str]:
    """Auto-detect one-level subfolders under /articles as categories."""
    if not ARTICLES_DIR.exists():
        return []
    cats = []
    for d in ARTICLES_DIR.iterdir():
        if not d.is_dir():
            continue
        if d.name.startswith("."):
            continue
        # reserve folder name commonly used for shared images
        if d.name.lower() in {"images", "assets"}:
            continue
        cats.append(d.name)
    cats.sort(key=lambda x: x.lower())
    return cats


def pick_category_cover(cat_dir: Path) -> str:
    """Return web path for category cover if exists (case-insensitive), else empty."""
    if not cat_dir.exists() or not cat_dir.is_dir():
        return ""

    # Build a lookup for case-insensitive filename matching
    try:
        children = {p.name.lower(): p for p in cat_dir.iterdir() if p.is_file()}
    except Exception:
        children = {}

    for name in COVER_CANDIDATES:
        p = children.get(name.lower())
        if p and p.exists():
            # 使用真实文件名（大小写正确）
            return f"/articles/{cat_dir.name}/{p.name}"
    return ""


# -------------------------
# Style & layout
# -------------------------
def base_css() -> str:
    return """
:root{
  --bg:#111412;
  --fg:#f3eee4;
  --muted:#b9b1a1;
  --muted-2:rgba(198,190,176,0.8);
  --accent:#c7a86b;
  --card:rgba(255,255,255,0.04);
  --line:rgba(255,255,255,0.06);
  --line2:rgba(217,202,162,0.22);
  --panel:rgba(44,50,46,0.82);
  --panel-strong:rgba(55,61,56,0.9);
  --shadow:0 18px 40px rgba(0,0,0,0.28);
  --serif:"Iowan Old Style","Palatino Linotype","Book Antiqua","Noto Serif SC","Songti SC","STSong",serif;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue","Segoe UI",Roboto,
    "PingFang SC","Hiragino Sans GB","Microsoft YaHei",Arial,sans-serif;
  background:var(--bg);
  color:var(--fg);
  line-height:1.75;
}
a{color:inherit;text-decoration:none}
a:hover{text-decoration:underline}

main{
  width:min(1180px, calc(100% - 32px));
  margin:0 auto;
  padding:96px 0 64px; /* space for fixed nav */
}

h1{
  margin:0;
  font-family:var(--serif);
  font-size:clamp(30px, 4.8vw, 50px);
  line-height:1.04;
  letter-spacing:-0.03em;
}

.hero-subtitle{
  margin:10px 0 0;
  color:rgba(198,190,176,0.72);
  font-size:17px;
  line-height:1.7;
  font-weight:300;
  letter-spacing:.01em;
}

.subtle{
  color:var(--muted);
  font-size:14px;
  line-height:1.65;
}

.hero{
  position:relative;
  display:grid;
  grid-template-columns:minmax(0, 1.22fr) minmax(240px, 0.78fr);
  gap:18px;
  padding:18px;
  border:1px solid var(--line);
  border-radius:28px;
  background:
    linear-gradient(135deg, rgba(50,56,51,0.92), rgba(31,35,33,0.88)),
    var(--panel);
  box-shadow:var(--shadow);
  overflow:hidden;
}

.hero::after{
  content:"";
  position:absolute;
  inset:auto -14% -34% 30%;
  height:320px;
  background:radial-gradient(circle, rgba(199,168,107,0.12), transparent 70%);
  pointer-events:none;
}

.hero-copy,
.hero-panel{
  position:relative;
  z-index:1;
}

.hero-panel{
  display:grid;
  gap:14px;
  align-content:start;
}

.hero-line{
  margin:0;
  color:var(--muted);
  font-family:var(--serif);
  font-size:22px;
  line-height:1.42;
  font-weight:400;
  letter-spacing:-0.01em;
}

.panel-card{
  display:block;
  padding:14px 16px;
  border-radius:16px;
  border:1px solid var(--line);
  background:
    linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0)),
    var(--panel-strong);
  text-decoration:none;
  color:inherit;
}

.panel-label{
  color:var(--accent);
  font-size:11px;
  letter-spacing:0.2em;
  text-transform:uppercase;
  margin-bottom:10px;
}

.panel-copy{
  margin:0;
  color:var(--muted-2);
  font-size:12px;
  line-height:1.6;
}

.panel-quote{
  margin:0;
  color:rgba(224,214,194,0.76);
  font-family:var(--serif);
  font-size:18px;
  line-height:1.3;
}

.intro-line{
  margin:0;
  color:var(--muted);
  font-size:18px;
  line-height:1.85;
  font-weight:300;
  letter-spacing:.02em;
}

.section{
  margin-top:24px;
  padding:28px;
  border-radius:26px;
  border:1px solid var(--line);
  background:
    linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0)),
    rgba(40,45,42,0.76);
  box-shadow:var(--shadow);
}

.grid{
  display:grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap:18px;
}

.card{
  background:
    radial-gradient(circle at top right, rgba(199,168,107,0.1), transparent 35%),
    linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0)),
    rgba(255,255,255,0.04);
  border:1px solid var(--line);
  border-radius:20px;
  overflow:hidden;
  transition: transform .2s ease, border-color .2s ease, background .2s ease;
}
.card:hover{
  transform: translateY(-3px);
  border-color: var(--line2);
  background:
    radial-gradient(circle at top right, rgba(199,168,107,0.14), transparent 38%),
    linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0)),
    rgba(255,255,255,0.055);
}

.cover{
  width:100%;
  height:220px;
  background:#0b0b0b;
  display:flex;
  align-items:center;
  justify-content:center;
  border-bottom:1px solid var(--line);
}
.cover img{
  width:100%;
  height:100%;
  object-fit:cover;
  object-position:center;
  display:block;
}

.card-body{
  padding:16px 16px 18px;
}

.card-title{
  font-family:var(--serif);
  font-size:20px;
  margin:0 0 8px;
  line-height:1.24;
  color:#e4dccd;
}

.card-body .subtle{
  display:-webkit-box;
  -webkit-box-orient:vertical;
  -webkit-line-clamp:4;
  overflow:hidden;
  color:var(--muted);
}

.meta{
  display:flex;
  gap:10px;
  align-items:center;
  color:var(--muted);
  font-size:13px;
  margin-top:8px;
}

.badge{
  display:inline-block;
  padding:3px 9px;
  border-radius:999px;
  border:1px solid var(--line);
  color:var(--muted-2);
  font-size:12px;
}

.footer{
  margin-top:40px;
  padding-top:18px;
  border-top:1px solid rgba(255,255,255,.08);
  color:var(--muted);
  font-size:13px;
}

/* Article detail */
.article{
  color:rgba(236,229,216,0.9);
}
.article h1{margin-top:8px}
.article .subtle{
  color:rgba(185,177,161,0.72);
}
.article img{
  max-width:100%;
  height:auto;
  border-radius:12px;
  border:1px solid rgba(255,255,255,.05);
}
.article pre{
  background:rgba(255,255,255,.03);
  border:1px solid rgba(255,255,255,.05);
  padding:14px;
  border-radius:12px;
  overflow:auto;
  color:rgba(236,229,216,0.88);
}
.article code{
  font-family: ui-monospace,SFMono-Regular,Menlo,Monaco,"Cascadia Mono",
    "Segoe UI Mono",Consolas,monospace;
}
.article blockquote{
  margin:14px 0;
  padding:10px 14px;
  border-left:3px solid rgba(199,168,107,.4);
  color:rgba(198,190,176,0.86);
  background:rgba(255,255,255,.02);
  border-radius:10px;
}

.backbar{
  margin-top:22px;
  padding-top:16px;
  border-top:1px solid rgba(255,255,255,.08);
  display:flex;
  gap:14px;
  flex-wrap:wrap;
}
.backbar a{
  color:var(--muted);
}
.backbar a:hover{
  color:var(--fg);
  text-decoration:underline;
}

@media (max-width: 860px){
  main{
    width:min(100% - 28px, 760px);
    padding:90px 0 56px;
  }

  .hero{
    grid-template-columns:1fr;
  }

  .section{
    padding:22px;
  }

  .grid{
    grid-template-columns:1fr;
  }

  .cover{
    height:200px;
  }
}
"""


def wrap_page(
    page_title: str,
    current_key: str,
    body_html: str,
    description: str = "",
    canonical_path: str = "",
    og_type: str = "article",
) -> str:
    safe_title = html.escape(page_title)
    safe_description = html.escape(
        seo_description(description, f"{page_title} · {SITE_TITLE}")
    )
    canonical_url = absolute_url(canonical_path or "/")
    safe_canonical_url = html.escape(canonical_url)
    year = datetime.now().year
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="description" content="{safe_description}" />
  <link rel="canonical" href="{safe_canonical_url}" />
  <meta property="og:site_name" content="{SITE_TITLE}" />
  <meta property="og:title" content="{safe_title} · {SITE_TITLE}" />
  <meta property="og:description" content="{safe_description}" />
  <meta property="og:type" content="{html.escape(og_type)}" />
  <meta property="og:url" content="{safe_canonical_url}" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{safe_title} · {SITE_TITLE}" />
  <meta name="twitter:description" content="{safe_description}" />
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
        extensions=["extra", "tables", "fenced_code", "toc"],
        output_format="html5",
    )


# -------------------------
# Generation
# -------------------------
def generate_article_pages(categories: list[str]):
    """
    For each category folder: generate article detail pages (md -> html beside md)
    Return dict: {cat: [ {title,date,href,excerpt} ... ] } sorted by newest first
    """
    category_articles: dict[str, list[dict]] = {}

    for cat in categories:
        cat_dir = ARTICLES_DIR / cat
        if not cat_dir.exists() or not cat_dir.is_dir():
            print(f"Warning: Category directory missing: {cat_dir}")
            category_articles[cat] = []
            continue

        md_files = sorted(
            [p for p in cat_dir.iterdir() if p.is_file() and p.suffix.lower() == ".md"],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        items = []

        for md_path in md_files:
            md_text = read_text(md_path)
            stem = md_path.stem

            title = extract_title(md_text, fallback=stem)
            mtime = md_path.stat().st_mtime
            date_str = fmt_date(mtime)
            summary = excerpt_from_md(md_text, max_len=140)

            md_body = strip_first_h1(md_text)
            content_html = render_markdown(md_body)
            content_html = fix_html_resource_cases(content_html, md_path.parent)

            out_path = md_path.with_suffix(".html")  # keep beside md

            detail_body = f"""
<article class="article">
  <h1>{html.escape(title)}</h1>
  <div class="subtle">{html.escape(date_str)}</div>
  <div style="height:14px"></div>
  {content_html}
  <div class="backbar">
    <a href="/articles/{html.escape(category_slug(cat))}.html">← 返回本栏目</a>
    <a href="/articles.html">← 返回随笔首页</a>
  </div>
</article>
""".strip()

            write_text(
                out_path,
                wrap_page(
                    title,
                    "articles",
                    detail_body,
                    description=summary,
                    canonical_path=f"/articles/{cat}/{stem}.html",
                ),
            )

            items.append(
                {
                    "title": title,
                    "date": date_str,
                    "href": f"/articles/{cat}/{stem}.html",
                    "excerpt": summary,
                    "mtime": mtime,
                }
            )

        category_articles[cat] = items
        print(f"✅ {cat} 类别下生成文章页：{len(items)} 篇")

    return category_articles


def generate_category_index(cat: str, items: list[dict]):
    cat_title = category_display_name(cat)
    latest = items[0]["date"] if items else ""
    if items:
        cards = []
        for it in items:
            cards.append(
                f"""
<a class="card" href="{html.escape(it["href"])}">
  <div class="card-body">
    <div class="card-title">{html.escape(it["title"])}</div>
    <div class="subtle">{html.escape(it.get("excerpt",""))}</div>
    <div class="meta">
      <span class="badge">{html.escape(it["date"])}</span>
    </div>
  </div>
</a>
""".strip()
            )

        body = f"""
<section class="hero">
  <div class="hero-copy">
    <h1>{html.escape(cat_title)}</h1>
    <p class="hero-subtitle">写作并不是结论，而是把经验通过不同视角慢慢放回结构中的过程。</p>
  </div>
  <div class="hero-panel">
    <a class="panel-card" href="/articles.html">
      <div class="panel-label">Back</div>
      <p class="panel-copy">← 返回随笔首页</p>
    </a>
  </div>
</section>

<section class="section">
  <div class="grid">
    {''.join(cards)}
  </div>
</section>
""".strip()
    else:
        body = f"""
<section class="hero">
  <div class="hero-copy">
    <h1>{html.escape(cat_title)}</h1>
    <p class="hero-subtitle">写作并不是结论，而是把经验通过不同视角慢慢放回结构中的过程。</p>
  </div>
  <div class="hero-panel">
    <a class="panel-card" href="/articles.html">
      <div class="panel-label">Back</div>
      <p class="panel-copy">← 返回随笔首页</p>
    </a>
  </div>
</section>

<section class="section">
  <div class="subtle">暂时还在沉淀中。</div>
</section>
""".strip()

    out_file = ARTICLES_DIR / f"{category_slug(cat)}.html"
    desc = f"{cat_title} 栏目文章列表，共 {len(items)} 篇，按最近更新时间排序。"
    write_text(
        out_file,
        wrap_page(
            f"{cat_title} · 随笔",
            "articles",
            body,
            description=desc,
            canonical_path=f"/articles/{category_slug(cat)}.html",
            og_type="website",
        ),
    )
    print(f"✅ 生成栏目页：{out_file}")


def generate_main_index(categories: list[str], category_articles: dict[str, list[dict]]):
    cards = []
    for cat in categories:
        cat_dir = ARTICLES_DIR / cat
        cover = pick_category_cover(cat_dir)
        count = len(category_articles.get(cat, []))

        # latest date (if any)
        latest = ""
        if count:
            latest = category_articles[cat][0]["date"]

        cover_html = ""
        if cover:
            cover_html = f'<div class="cover"><img src="{html.escape(cover)}" alt="cover"></div>'

        subtitle = f"{count} 篇"
        if latest:
            subtitle += f" · 最近：{latest}"

        cards.append(
            f"""
<a class="card" href="/articles/{html.escape(category_slug(cat))}.html">
  {cover_html}
  <div class="card-body">
    <div class="card-title">{html.escape(category_display_name(cat))}</div>
    <div class="subtle">{html.escape(subtitle)}</div>
  </div>
</a>
""".strip()
        )

    total = sum(len(category_articles.get(cat, [])) for cat in categories)
    body = f"""
<section class="hero">
  <div class="hero-copy">
    <h1>随笔</h1>
    <p class="hero-subtitle">写作并不是结论，而是把经验通过不同视角慢慢放回结构中的过程。</p>
  </div>
  <div class="hero-panel">
    <div class="panel-card">
      <div class="panel-label">Essays</div>
      <p class="panel-copy">{len(categories)} 个栏目 · {total} 篇</p>
    </div>
  </div>
</section>

<section class="section">
  <div class="grid">
    {''.join(cards)}
  </div>
</section>
""".strip()

    desc = f"RedRocks 随笔首页，从佛法、杂文、摄影、旅行与 TAP 进入书写的不同侧面，共 {total} 篇。"
    write_text(
        INDEX_OUT,
        wrap_page(
            "随笔",
            "articles",
            body,
            description=desc,
            canonical_path="/articles.html",
            og_type="website",
        ),
    )
    print(f"✅ 生成随笔首页：{INDEX_OUT}")


def main():
    if not ARTICLES_DIR.exists():
        print(f"ERROR: 路径不存在: {ARTICLES_DIR}")
        sys.exit(1)

    categories = discover_categories()
    if not categories:
        print("ERROR: 未发现任何栏目。请在 articles/ 下创建子目录（例如 travel/ tap/ ...）")
        sys.exit(1)

    category_articles = generate_article_pages(categories)

    for cat, items in category_articles.items():
        generate_category_index(cat, items)

    generate_main_index(categories, category_articles)


if __name__ == "__main__":
    main()
