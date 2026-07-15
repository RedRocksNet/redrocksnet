#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import html
import json
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
LATEST_OUT = ARTICLES_DIR / "latest.json" # 随笔首页顶部的最新文章入口
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

CATEGORY_NOTES = {
    "photography": "以影像与器材、观察与心境，进入摄影这一侧的书写。",
    "buddhism": "从经文、修行与日常体会，进入佛法这一侧的书写。",
    "misc": "那些不容易归类，却始终在心里盘旋的问题与文字。",
    "travel": "行走、所见与途中思绪，留给旅行这一册。",
    "tap": "关于时间、投影、结构与世界模型的长期思考。",
}

THEME_CURATION = [
    {
        "title": "家与安顿",
        "summary": "关于家、秩序、亲情、来处，以及人在世界里如何找到可以安身的地方。",
        "picks": [
            ("misc", "房里有猪：关于家的胡思乱想"),
            ("misc", "三金缕曲：风雪之义、知己之契、生死之情"),
        ],
    },
    {
        "title": "世界与文明",
        "summary": "关于文明比较、历史逻辑、合法性来源，以及不同生存方式在世界中的冲突与并置。",
        "picks": [
            ("misc", "不同文明的合法性本体"),
            ("misc", "贪婪：文明的暗影与火种"),
            ("buddhism", "若无佛来：中国文明的另一种命运"),
        ],
    },
    {
        "title": "观看与摄影",
        "summary": "关于摄影、器材、观察、影像与心境，文字在这里继续延伸照片没有说完的那部分。",
        "picks": [
            ("photography", "一个摄影师的独白"),
            ("photography", "镜底心归：摄影里的自我心境修行"),
            ("photography", "过期黑白胶卷使用笔记"),
        ],
    },
    {
        "title": "修行与佛法",
        "summary": "关于经文、手书、修行体会与佛法理解，既谈经典，也谈日常之中的安顿与放下。",
        "picks": [
            ("buddhism", "抄经随笔"),
            ("buddhism", "读经不执相：《大般涅槃经》客医喻"),
            ("buddhism", "天龙八部：藏于佛殿、流于江湖，未被读懂的佛教文化符号"),
        ],
    },
    {
        "title": "时间与结构",
        "summary": "关于 TAP、投影、维度、结构与世界模型，试着为经验寻找一种更稳定的框架。",
        "picks": [
            ("TAP", "穿越维度的低语：TAP理论与宇宙、哲学、空性的全景对话"),
            ("TAP", "身体受限、意识扩张与高维观察：TAP 理论下的多维存在模型初探"),
            ("TAP", "TAP理论里，投影界面的物理逻辑与《金刚经》第二十七品的结构同构性研究"),
        ],
    },
]


def category_display_name(dirname: str) -> str:
    """把随笔子目录名转换为要显示的‘中文（English）’。未知目录则原样返回。"""
    key = (dirname or "").strip().lower()
    return CATEGORY_ZH_EN.get(key, dirname)


def category_slug(dirname: str) -> str:
    """Normalize category page filenames/URLs so links stay stable on case-sensitive hosts."""
    return (dirname or "").strip().lower()


def category_note(dirname: str) -> str:
    return CATEGORY_NOTES.get(category_slug(dirname), "从这一册进入对应的书写。")


def find_curated_item(category_articles: dict[str, list[dict]], cat: str, title: str):
    for it in category_articles.get(cat, []):
        if it.get("title") == title:
            return it
    return None


def find_latest_article(category_articles: dict[str, list[dict]]):
    latest_item = None
    latest_cat = ""
    latest_mtime = -1.0

    for cat, items in category_articles.items():
        if not items:
            continue
        candidate = items[0]
        mtime = float(candidate.get("mtime") or 0.0)
        if mtime > latest_mtime:
            latest_mtime = mtime
            latest_item = candidate
            latest_cat = cat

    return latest_cat, latest_item


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


def load_article_metadata(md_path: Path) -> dict:
    meta_path = md_path.with_suffix(".publisher.json")
    if not meta_path.exists():
        return {}
    try:
        return json.loads(read_text(meta_path))
    except Exception:
        return {}


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
a:hover{text-decoration:none}

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

.panel-link{
  display:flex;
  flex-direction:column;
  gap:6px;
  padding:14px 15px 13px;
  border-radius:16px;
  border:1px solid rgba(255,255,255,0.08);
  background:
    linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0)),
    rgba(17,20,18,0.32);
  color:inherit;
  text-decoration:none;
  transition:transform .18s ease, border-color .18s ease, background .18s ease;
}

.panel-link:hover{
  transform:translateY(-1px);
  border-color:var(--line2);
  background:
    linear-gradient(180deg, rgba(255,255,255,0.055), rgba(255,255,255,0)),
    rgba(17,20,18,0.38);
}

.panel-link-title{
  color:#efe6d7;
  font-family:var(--serif);
  font-size:18px;
  line-height:1.35;
  letter-spacing:-0.02em;
}

.panel-link-meta{
  color:var(--muted-2);
  font-size:12px;
  letter-spacing:0.08em;
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

.section-head{
  display:flex;
  align-items:flex-end;
  justify-content:space-between;
  gap:18px;
  margin-bottom:18px;
}

.section-kicker{
  color:var(--accent);
  font-size:11px;
  letter-spacing:.2em;
  text-transform:uppercase;
  margin-bottom:10px;
}

.section-title{
  margin:0;
  font-family:var(--serif);
  font-size:clamp(24px, 3.2vw, 38px);
  line-height:1.08;
  letter-spacing:-0.025em;
}

.section-note{
  margin:10px 0 0;
  color:var(--muted);
  font-size:14px;
  line-height:1.7;
}

.grid{
  display:grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap:18px;
}

.theme-grid{
  display:grid;
  grid-template-columns:repeat(2, minmax(0, 1fr));
  gap:18px;
}

.theme-card{
  padding:20px 20px 18px;
  border-radius:20px;
  border:1px solid var(--line);
  background:
    radial-gradient(circle at top right, rgba(199,168,107,0.08), transparent 35%),
    linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0)),
    rgba(255,255,255,0.035);
}

.theme-title{
  margin:0 0 8px;
  color:#e8dfcf;
  font-family:var(--serif);
  font-size:24px;
  line-height:1.12;
  letter-spacing:-0.02em;
}

.theme-summary{
  margin:0;
  color:var(--muted);
  font-size:14px;
  line-height:1.75;
}

.theme-links{
  margin-top:16px;
  display:grid;
  gap:10px;
}

.theme-link{
  display:block;
  padding:12px 14px;
  border-radius:14px;
  border:1px solid rgba(255,255,255,0.05);
  background:rgba(255,255,255,0.025);
  transition:transform .18s ease, border-color .18s ease, background .18s ease;
}

.theme-link:hover{
  transform:translateY(-2px);
  border-color:var(--line2);
  background:rgba(255,255,255,0.04);
}

.theme-link-label{
  display:block;
  color:var(--accent);
  font-size:11px;
  letter-spacing:.16em;
  text-transform:uppercase;
  margin-bottom:6px;
}

.theme-link-title{
  display:block;
  color:#e5dccd;
  font-size:16px;
  line-height:1.45;
}

.shelf-grid{
  display:grid;
  grid-template-columns:repeat(5, minmax(0, 1fr));
  gap:16px;
}

.spine-card{
  position:relative;
  min-height:360px;
  border-radius:22px;
  overflow:hidden;
  border:1px solid var(--line);
  background:
    linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.01)),
    rgba(47,53,49,0.92);
  box-shadow:var(--shadow);
  transition:transform .22s ease, border-color .22s ease, box-shadow .22s ease;
}

.spine-card:hover{
  transform:translateY(-4px);
  border-color:var(--line2);
  box-shadow:0 22px 42px rgba(0,0,0,0.34);
}

.spine-card::before{
  content:"";
  position:absolute;
  inset:0;
  background:
    linear-gradient(180deg, rgba(0,0,0,0.08), rgba(0,0,0,0.32)),
    var(--spine-image, linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0)));
  background-size:cover;
  background-position:center;
  opacity:.32;
}

.spine-card::after{
  content:"";
  position:absolute;
  top:0;
  bottom:0;
  left:16px;
  width:1px;
  background:rgba(217,202,162,0.22);
}

.spine-inner{
  position:relative;
  z-index:1;
  display:flex;
  flex-direction:column;
  justify-content:space-between;
  min-height:360px;
  padding:18px 18px 18px 30px;
}

.spine-top{
  display:flex;
  flex-direction:column;
  gap:14px;
}

.spine-kicker{
  color:var(--accent);
  font-size:11px;
  letter-spacing:.18em;
  text-transform:uppercase;
}

.spine-title{
  margin:0;
  color:#efe6d7;
  font-family:var(--serif);
  font-size:26px;
  line-height:1.05;
  letter-spacing:-0.03em;
  writing-mode:vertical-rl;
  text-orientation:mixed;
  max-height:190px;
}

.spine-note{
  color:rgba(198,190,176,0.78);
  font-size:12px;
  line-height:1.65;
}

.spine-meta{
  display:flex;
  flex-direction:column;
  gap:8px;
  color:rgba(198,190,176,0.82);
  font-size:12px;
}

.spine-badge{
  display:inline-flex;
  align-self:flex-start;
  padding:3px 9px;
  border-radius:999px;
  border:1px solid rgba(255,255,255,0.09);
  background:rgba(17,20,18,0.26);
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

.card-body .subtle.subtle-empty{
  -webkit-line-clamp:1;
  min-height:1.35em;
  opacity:0.38;
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
  display:block;
  max-width:100%;
  width:auto;
  height:auto;
  margin:18px auto;
  border-radius:12px;
  border:1px solid rgba(255,255,255,.05);
  box-shadow:0 10px 24px rgba(0,0,0,.18);
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

.article p a:hover,
.article li a:hover,
.article blockquote a:hover{
  text-decoration:underline;
}

.read-tools{
  position:fixed;
  top:92px;
  right:24px;
  z-index:30;
  display:flex;
  align-items:center;
  gap:10px;
  padding:10px 12px;
  border-radius:14px;
  border:1px solid rgba(255,255,255,.06);
  background:rgba(33,38,35,.78);
  backdrop-filter:blur(10px);
  box-shadow:0 10px 24px rgba(0,0,0,.2);
}

.read-back{
  color:var(--accent);
  font-size:12px;
  line-height:1;
  text-decoration:none;
  white-space:nowrap;
}

.read-back:hover{
  color:#d9caa2;
  text-decoration:none;
}

.read-mode{
  display:inline-flex;
  align-items:center;
  gap:4px;
  padding-left:10px;
  border-left:1px solid rgba(255,255,255,.08);
}

.mode-btn{
  border:0;
  background:transparent;
  color:rgba(198,190,176,.72);
  font-size:11px;
  line-height:1;
  padding:4px 6px;
  border-radius:999px;
  cursor:pointer;
}

.mode-btn.active{
  color:var(--accent);
  background:rgba(199,168,107,.12);
}

body.reading-soft .article{
  color:rgba(224,216,202,0.82);
}

body.reading-soft .article .subtle{
  color:rgba(185,177,161,0.64);
}

body.reading-soft .article pre{
  background:rgba(255,255,255,.02);
  border-color:rgba(255,255,255,.04);
  color:rgba(224,216,202,0.82);
}

body.reading-soft .article blockquote{
  color:rgba(191,183,170,0.78);
  background:rgba(255,255,255,.015);
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

  .shelf-grid{
    grid-template-columns:repeat(2, minmax(0, 1fr));
  }

  .spine-card,
  .spine-inner{
    min-height:300px;
  }

  .spine-title{
    font-size:23px;
    max-height:160px;
  }

  .cover{
    height:200px;
  }

  .read-tools{
    top:84px;
    right:14px;
    padding:8px 10px;
  }
}

@media (max-width: 560px){
  main{
    width:min(100% - 18px, 760px);
    padding:78px 0 18px;
  }

  .hero{
    padding:14px;
    gap:12px;
    border-radius:22px;
  }

  .hero-copy{
    min-width:0;
  }

  .hero-subtitle{
    font-size:15px;
    line-height:1.6;
    margin-top:8px;
  }

  .panel-card{
    padding:14px;
    border-radius:16px;
  }

  .panel-copy{
    font-size:12px;
  }

  .panel-link{
    padding:13px 14px 12px;
  }

  .panel-link-title{
    font-size:17px;
  }

  .panel-quote{
    display:none;
  }

  .section{
    margin-top:14px;
    padding:14px;
    border-radius:20px;
  }

  .shelf-grid{
    grid-template-columns:1fr;
    gap:10px;
  }

  .spine-card,
  .spine-inner{
    min-height:126px;
  }

  .spine-card{
    border-radius:18px;
  }

  .spine-inner{
    padding:12px 12px 12px 16px;
  }

  .spine-top{
    gap:6px;
  }

  .spine-title{
    font-size:17px;
    line-height:1.08;
    writing-mode:horizontal-tb;
    text-orientation:initial;
    max-height:none;
  }

  .spine-note{
    display:none;
  }

  .spine-meta{
    gap:6px;
  }

  .spine-badge{
    padding:2px 8px;
    font-size:11px;
  }

  .read-tools{
    left:14px;
    right:auto;
    max-width:calc(100% - 28px);
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
            meta = load_article_metadata(md_path)

            title = extract_title(md_text, fallback=stem)
            mtime = md_path.stat().st_mtime
            date_str = fmt_date(mtime)
            summary = (meta.get("summary") or "").strip()

            md_body = strip_first_h1(md_text)
            content_html = render_markdown(md_body)
            content_html = fix_html_resource_cases(content_html, md_path.parent)

            out_path = md_path.with_suffix(".html")  # keep beside md

            detail_body = f"""
<div class="read-tools" aria-label="阅读工具">
  <a class="read-back" href="/articles/{html.escape(category_slug(cat))}.html">← 返回栏目</a>
  <div class="read-mode" aria-label="阅读模式">
    <button class="mode-btn active" data-read-mode="standard" type="button">标准</button>
    <button class="mode-btn" data-read-mode="soft" type="button">柔和</button>
  </div>
</div>

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

<script>
  (function () {{
    const storageKey = 'rr-reading-mode';
    const body = document.body;
    const buttons = document.querySelectorAll('[data-read-mode]');

    function applyMode(mode) {{
      body.classList.toggle('reading-soft', mode === 'soft');
      buttons.forEach((btn) => {{
        btn.classList.toggle('active', btn.dataset.readMode === mode);
      }});
    }}

    const saved = localStorage.getItem(storageKey) || 'standard';
    applyMode(saved);

    buttons.forEach((btn) => {{
      btn.addEventListener('click', () => {{
        const mode = btn.dataset.readMode || 'standard';
        localStorage.setItem(storageKey, mode);
        applyMode(mode);
      }});
    }});
  }})();
</script>
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
            excerpt = (it.get("excerpt") or "").strip()
            excerpt_html = (
                f'<div class="subtle">{html.escape(excerpt)}</div>'
                if excerpt
                else '<div class="subtle subtle-empty" aria-hidden="true">&nbsp;</div>'
            )
            cards.append(
                f"""
<a class="card" href="{html.escape(it["href"])}">
  <div class="card-body">
    <div class="card-title">{html.escape(it["title"])}</div>
    {excerpt_html}
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


def generate_latest_article_feed(category_articles: dict[str, list[dict]]):
    latest_item = None
    latest_cat = ""
    latest_mtime = -1.0

    for cat, items in category_articles.items():
        if not items:
            continue
        candidate = items[0]
        mtime = float(candidate.get("mtime") or 0.0)
        if mtime > latest_mtime:
            latest_mtime = mtime
            latest_item = candidate
            latest_cat = cat

    payload = {
        "title": latest_item["title"] if latest_item else "",
        "href": latest_item["href"] if latest_item else "/articles.html",
        "date": latest_item["date"] if latest_item else "",
        "category": category_display_name(latest_cat) if latest_item else "",
        "category_slug": category_slug(latest_cat) if latest_item else "",
    }
    write_text(
        LATEST_OUT,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    print(f"✅ 生成最新文章索引：{LATEST_OUT}")


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

        subtitle = f"{count} 篇"
        if latest:
            subtitle += f" · 最近：{latest}"

        spine_style = ""
        if cover:
            spine_style = f' style="--spine-image:url(\'{html.escape(cover)}\')"'

        cards.append(
            f"""
<a class="spine-card" href="/articles/{html.escape(category_slug(cat))}.html"{spine_style}>
  <div class="spine-inner">
    <div class="spine-top">
      <div class="spine-kicker">Essays</div>
      <div class="spine-title">{html.escape(category_display_name(cat))}</div>
      <div class="spine-note">{html.escape(category_note(cat))}</div>
    </div>
    <div class="spine-meta">
      <span class="spine-badge">{html.escape(subtitle)}</span>
    </div>
  </div>
</a>
""".strip()
            )

    total = sum(len(category_articles.get(cat, [])) for cat in categories)
    latest_cat, latest_item = find_latest_article(category_articles)
    latest_href = html.escape(latest_item["href"]) if latest_item else "/articles.html"
    latest_title = html.escape(latest_item["title"]) if latest_item else "最新文章"
    latest_meta_parts = []
    if latest_item:
        latest_meta_parts = [category_display_name(latest_cat), latest_item["date"]]
    latest_meta = " · ".join(part for part in latest_meta_parts if part)

    body = f"""
<section class="hero">
  <div class="hero-copy">
    <h1>随笔</h1>
    <p class="hero-subtitle">写作并不是结论，而是把经验通过不同视角慢慢放回结构中的过程。</p>
  </div>
  <div class="hero-panel">
    <div class="panel-card">
      <div class="panel-label">Latest</div>
      <a
        class="panel-link"
        id="latest-article-link"
        href="{latest_href}"
        data-fallback-title="{latest_title}"
        data-fallback-meta="{html.escape(latest_meta)}"
      >
        <span class="panel-link-title" id="latest-article-title">{latest_title}</span>
        <span class="panel-link-meta" id="latest-article-meta">{html.escape(latest_meta)}</span>
      </a>
      <p class="panel-quote">像翻开书脊一样进入，不再摆出多套入口。</p>
    </div>
  </div>
</section>

<section class="section">
  <div class="shelf-grid">
    {''.join(cards)}
  </div>
</section>

<script>
  (async () => {{
    const link = document.getElementById('latest-article-link');
    const titleEl = document.getElementById('latest-article-title');
    const metaEl = document.getElementById('latest-article-meta');
    if (!link || !titleEl || !metaEl) return;

    const fallbackTitle = link.dataset.fallbackTitle || titleEl.textContent || '';
    const fallbackMeta = link.dataset.fallbackMeta || metaEl.textContent || '';

    try {{
      const response = await fetch('/articles/latest.json', {{ cache: 'no-store' }});
      if (!response.ok) throw new Error(`latest.json ${{response.status}}`);
      const data = await response.json();
      if (!data || !data.href || !data.title) throw new Error('invalid latest payload');

      link.href = data.href;
      titleEl.textContent = data.title;
      metaEl.textContent = [data.category, data.date].filter(Boolean).join(' · ');
      link.setAttribute('aria-label', `最新文章：${{data.title}}`);
    }} catch (err) {{
      titleEl.textContent = fallbackTitle;
      metaEl.textContent = fallbackMeta;
    }}
  }})();
</script>
""".strip()

    desc = f"RedRocks 随笔首页，以书脊式入口浏览摄影、杂文、佛法、旅行与 TAP，共 {total} 篇。"
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

    generate_latest_article_feed(category_articles)
    generate_main_index(categories, category_articles)


if __name__ == "__main__":
    main()
