from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import markdown

from .config_service import load_categories, load_site_config
from .metadata_service import load_metadata, ensure_metadata
from .utils import excerpt, first_h1, read_json, strip_first_h1, today_iso, unique_by_key


def category_by_id(root: Path, category_id: str) -> dict:
    cats = load_categories(root).get("categories", [])
    for cat in cats:
        if cat["id"] == category_id:
            return cat
    raise ValueError(f"unknown category: {category_id}")


def category_dir(root: Path, category_id: str) -> Path:
    cat = category_by_id(root, category_id)
    return root / "articles" / cat["directory"]


def category_id_from_directory(root: Path, directory: str) -> str:
    cats = load_categories(root).get("categories", [])
    for cat in cats:
        if cat["directory"].lower() == directory.lower():
            return cat["id"]
    return directory.lower()


def category_name(root: Path, category_id: str) -> str:
    return category_by_id(root, category_id)["name"]


def article_candidates(root: Path, category_dir: Path) -> list[Path]:
    result: list[Path] = []
    if not category_dir.exists():
        return result
    by_stem: dict[str, Path] = {}
    for path in sorted(category_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.suffix.lower() not in {".md", ".html"}:
            continue
        if path.name == f"{category_dir.name}.html":
            continue
        if path.name.endswith(".publisher.json"):
            continue
        existing = by_stem.get(path.stem)
        if existing is None:
            by_stem[path.stem] = path
        elif existing.suffix.lower() != ".md" and path.suffix.lower() == ".md":
            by_stem[path.stem] = path
    for stem in sorted(by_stem):
        result.append(by_stem[stem])
    return result


def infer_source_file(category_dir: Path, stem: str) -> Path | None:
    md = category_dir / f"{stem}.md"
    html_path = category_dir / f"{stem}.html"
    if md.exists():
        return md
    if html_path.exists():
        return html_path
    return None


def load_article_source(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".md":
        title = first_h1(text) or path.stem
        return {
            "format": "markdown",
            "title": title,
            "plain_text": excerpt(text, 2000),
            "html": markdown.markdown(strip_first_h1(text), extensions=["extra", "tables", "fenced_code"]),
            "text": text,
        }
    return {
        "format": "html",
        "title": extract_title_from_html(text) or path.stem,
        "plain_text": html_to_text(text),
        "html": extract_article_html(text),
        "text": text,
    }


def extract_title_from_html(text: str) -> str:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", text, flags=re.I | re.S)
    if not m:
        return ""
    return re.sub(r"<[^>]+>", "", m.group(1)).strip()


def extract_article_html(text: str) -> str:
    m = re.search(r"<article[^>]*class=\"article\"[^>]*>(.*?)</article>", text, flags=re.I | re.S)
    if m:
        return m.group(1).strip()
    m = re.search(r"<body[^>]*>(.*?)</body>", text, flags=re.I | re.S)
    if m:
        return m.group(1).strip()
    return text


def html_to_text(text: str) -> str:
    cleaned = re.sub(r"<script.*?</script>", " ", text, flags=re.I | re.S)
    cleaned = re.sub(r"<style.*?</style>", " ", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def scan_articles(root: Path) -> list[dict[str, Any]]:
    cats = load_categories(root).get("categories", [])
    results: list[dict[str, Any]] = []
    for cat in cats:
        cat_dir = root / "articles" / cat["directory"]
        if not cat_dir.exists():
            continue
        for path in article_candidates(root, cat_dir):
            source = load_article_source(path)
            meta = load_metadata(path) or {}
            article_id = meta.get("article_id") or f"ephemeral:{cat['id']}:{path.stem}"
            title = meta.get("title") or source["title"]
            summary = meta.get("summary") or ""
            results.append(
                {
                    "article_id": article_id,
                    "title": title,
                    "summary": summary,
                    "category_id": cat["id"],
                    "category_name": cat["name"],
                    "category_directory": cat["directory"],
                    "path": str(path.relative_to(root)),
                    "source_format": meta.get("source_format") or source["format"],
                    "status": meta.get("status") or ("published" if path.suffix.lower() == ".html" else "draft"),
                    "slug": meta.get("slug") or path.stem,
                    "local_html_url": path.with_suffix(".html").resolve().as_uri(),
                    "canonical_url": meta.get("canonical_url") or f"{load_site_config(root).site_base_url}/articles/{cat['directory']}/{(meta.get('slug') or path.stem)}.html",
                    "updated_date": meta.get("updated_date") or today_iso(),
                    "published_date": meta.get("published_date") or today_iso(),
                    "has_metadata": bool(meta),
                }
            )
    results.sort(key=lambda item: (item["updated_date"], item["title"]), reverse=True)
    return results


def article_paths(root: Path, category_id: str, slug: str) -> dict[str, Path]:
    cat = category_by_id(root, category_id)
    cat_dir = root / "articles" / cat["directory"]
    return {
        "directory": cat_dir,
        "markdown": cat_dir / f"{slug}.md",
        "html": cat_dir / f"{slug}.html",
        "meta": cat_dir / f"{slug}.publisher.json",
    }


def resolve_article_by_id(root: Path, article_id: str) -> dict | None:
    for article in scan_articles(root):
        if article["article_id"] == article_id:
            return article
    return None


def load_article_detail(root: Path, article_id: str) -> dict | None:
    found = resolve_article_by_id(root, article_id)
    if not found:
        return None
    cat = category_by_id(root, found["category_id"])
    source_path = infer_source_file(root / "articles" / cat["directory"], found["slug"])
    if not source_path:
        return found
    source = load_article_source(source_path)
    meta = load_metadata(source_path) or {}
    found["content_html"] = source["html"]
    found["plain_text"] = source["plain_text"]
    found["raw_text"] = source["text"]
    found["source_path"] = str(source_path.relative_to(root))
    found["local_html_url"] = source_path.with_suffix(".html").resolve().as_uri()
    found["metadata"] = meta
    return found


def resolve_article_paths_from_metadata(root: Path, metadata: dict) -> dict[str, Path]:
    return article_paths(root, metadata["category_id"], metadata["slug"])


def materialize_metadata(root: Path, payload: dict, source_path: Path | None = None) -> dict:
    cat = category_by_id(root, payload["category_id"])
    slug = payload["slug"]
    paths = article_paths(root, cat["id"], slug)
    meta = {
        "schema_version": 1,
        "article_id": payload.get("article_id") or None,
        "title": payload.get("title", ""),
        "english_title": payload.get("english_title", ""),
        "subtitle": payload.get("subtitle", ""),
        "summary": payload.get("summary", ""),
        "author": payload.get("author", load_site_config(root).author_default),
        "published_date": payload.get("published_date") or today_iso(),
        "updated_date": payload.get("updated_date") or today_iso(),
        "status": payload.get("status", "draft"),
        "slug": slug,
        "category_id": cat["id"],
        "category_name": cat["name"],
        "themes": payload.get("themes") or [],
        "tags": unique_by_key(payload.get("tags") or []),
        "featured": bool(payload.get("featured", False)),
        "source_format": payload.get("source_format", "paste"),
        "source_path": str(source_path.relative_to(root)) if source_path else payload.get("source_path"),
        "article_relative_path": str(paths["markdown"].relative_to(root)),
        "canonical_url": payload.get("canonical_url") or f"https://www.redrocks.net/articles/{cat['directory']}/{slug}.html",
        "previous_paths": payload.get("previous_paths") or [],
        "redirect_from": payload.get("redirect_from") or [],
    }
    if not meta["article_id"]:
        meta["article_id"] = payload.get("article_id") or ""
    return meta
