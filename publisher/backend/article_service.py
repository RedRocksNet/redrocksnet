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


def article_metadata_candidates(category_dir: Path) -> list[Path]:
    if not category_dir.exists():
        return []
    return sorted(
        path
        for path in category_dir.iterdir()
        if path.is_file() and not path.name.startswith(".") and path.name.endswith(".publisher.json")
    )


def metadata_slug(metadata_path: Path | None) -> str:
    if not metadata_path:
        return ""
    name = metadata_path.name
    suffix = ".publisher.json"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return metadata_path.stem


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


def sanitize_summary_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return ""
    if "<" in cleaned or ">" in cleaned:
        return ""
    if len(cleaned) > 220:
        return ""
    return cleaned


def article_sync_state(status: str, source_exists: bool, public_html_exists: bool, metadata_exists: bool) -> str:
    if metadata_exists and not source_exists and not public_html_exists:
        return "metadata-only"
    if status == "published":
        if source_exists and public_html_exists:
            return "synced"
        if source_exists and not public_html_exists:
            return "missing-public"
        if public_html_exists and not source_exists:
            return "missing-source"
        return "metadata-only"
    if source_exists and public_html_exists:
        return "draft-synced"
    if source_exists and not public_html_exists:
        return "draft-local-only"
    if public_html_exists and not source_exists:
        return "draft-public-only"
    return "metadata-only"


def build_article_record(
    root: Path,
    cat: dict[str, Any],
    source_path: Path | None,
    metadata_path: Path | None,
) -> dict[str, Any]:
    source = load_article_source(source_path) if source_path else None
    meta = {}
    if source_path:
        meta = load_metadata(source_path) or {}
    elif metadata_path and metadata_path.exists():
        meta = read_json(metadata_path, {}) or {}
    fallback_slug = source_path.stem if source_path else metadata_slug(metadata_path)
    slug = meta.get("slug") or fallback_slug
    paths = article_paths(root, cat["id"], slug or fallback_slug)
    source_exists = bool(source_path and source_path.exists())
    metadata_exists = bool(metadata_path and metadata_path.exists())
    public_html_path = source_path.with_suffix(".html") if source_path else paths["html"]
    public_html_exists = public_html_path.exists()
    article_id = meta.get("article_id") or f"ephemeral:{cat['id']}:{slug or fallback_slug or 'unknown'}"
    title = meta.get("title") or (source["title"] if source else (slug or fallback_slug))
    summary = sanitize_summary_text(meta.get("summary") or "")
    status = meta.get("status") or ("published" if public_html_exists and source_exists else "draft")
    record_path = source_path or metadata_path or paths["markdown"]
    sync_state = article_sync_state(status, source_exists, public_html_exists, metadata_exists)
    canonical_url = meta.get("canonical_url") or f"{load_site_config(root).site_base_url}/articles/{cat['directory']}/{(slug or paths['html'].stem)}.html"
    local_html_url = public_html_path.resolve().as_uri() if public_html_exists else None
    return {
        "article_id": article_id,
        "title": title,
        "summary": summary,
        "category_id": cat["id"],
        "category_name": cat["name"],
        "category_directory": cat["directory"],
        "path": str(record_path.relative_to(root)),
        "source_path": str(source_path.relative_to(root)) if source_path else meta.get("source_path"),
        "source_format": meta.get("source_format") or (source["format"] if source else "metadata"),
        "status": status,
        "slug": slug or paths["html"].stem,
        "local_html_url": local_html_url,
        "canonical_url": canonical_url,
        "updated_date": meta.get("updated_date") or today_iso(),
        "published_date": meta.get("published_date") or today_iso(),
        "has_metadata": bool(meta),
        "metadata_path": str(metadata_path.relative_to(root)) if metadata_path else None,
        "source_exists": source_exists,
        "public_html_exists": public_html_exists,
        "metadata_exists": metadata_exists,
        "sync_state": sync_state,
    }


def scan_articles(root: Path) -> list[dict[str, Any]]:
    cats = load_categories(root).get("categories", [])
    results: list[dict[str, Any]] = []
    for cat in cats:
        cat_dir = root / "articles" / cat["directory"]
        if not cat_dir.exists():
            continue
        seen_stems: set[str] = set()
        for path in article_candidates(root, cat_dir):
            seen_stems.add(path.stem)
            results.append(build_article_record(root, cat, path, path.with_suffix(".publisher.json")))
        for meta_path in article_metadata_candidates(cat_dir):
            if metadata_slug(meta_path) in seen_stems:
                continue
            results.append(build_article_record(root, cat, None, meta_path))
    results.sort(key=lambda item: (item["category_name"], item["updated_date"], item["title"]), reverse=True)
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
    source_path = None
    source_path_value = found.get("source_path")
    if source_path_value:
        candidate = root / source_path_value
        if candidate.exists():
            source_path = candidate
    if not source_path:
        source_path = infer_source_file(root / "articles" / cat["directory"], found["slug"])
    if not source_path:
        meta_path = Path(found["metadata_path"]) if found.get("metadata_path") else root / "articles" / cat["directory"] / f"{found['slug']}.publisher.json"
        if not meta_path.is_absolute():
            meta_path = root / meta_path
        if meta_path.exists():
            found["metadata"] = read_json(meta_path, {}) or {}
            found["metadata_path"] = str(meta_path.relative_to(root))
        return found
    source = load_article_source(source_path)
    meta = load_metadata(source_path) or {}
    found["content_html"] = source["html"]
    found["plain_text"] = source["plain_text"]
    found["raw_text"] = source["text"]
    found["source_path"] = str(source_path.relative_to(root))
    html_path = source_path.with_suffix(".html")
    found["local_html_url"] = html_path.resolve().as_uri() if html_path.exists() else None
    found["metadata"] = meta
    if "summary" in found:
        found["summary"] = sanitize_summary_text(found.get("summary") or "")
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
