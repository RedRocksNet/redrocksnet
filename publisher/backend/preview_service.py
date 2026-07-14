from __future__ import annotations

import html
from pathlib import Path

from . import article_service


def render_article_preview(root: Path, metadata: dict, html_body: str, mobile: bool = False) -> str:
    from generate_article import wrap_page

    category = article_service.category_by_id(root, metadata["category_id"])
    article_title = metadata.get("title") or metadata.get("slug") or "Untitled"
    detail_body = f"""
<article class="article">
  <h1>{html.escape(article_title)}</h1>
  <div class="subtle">{html.escape(metadata.get("published_date") or metadata.get("updated_date") or "")}</div>
  <div style="height:14px"></div>
  {html_body}
</article>
""".strip()
    page = wrap_page(
        article_title,
        "articles",
        detail_body,
        description=metadata.get("summary") or article_title,
        canonical_path=metadata.get("canonical_url") or f"/articles/{category['directory']}/{metadata['slug']}.html",
    )
    if mobile:
        page = page.replace(
            "<main>",
            '<main style="width:min(390px, calc(100% - 22px)); margin:0 auto; padding-top:24px;">',
        )
        page = page.replace("body{", "body{max-width:390px;margin:0 auto;background:#111412;")
    return page

