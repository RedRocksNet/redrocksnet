from __future__ import annotations

import uuid
from dataclasses import dataclass, asdict
from pathlib import Path

from .utils import normalize_tag, unique_by_key, today_iso, now_iso, read_json, write_json_atomic


@dataclass
class ArticleMetadata:
    schema_version: int = 1
    article_id: str = ""
    title: str = ""
    english_title: str = ""
    subtitle: str = ""
    summary: str = ""
    author: str = "RedRocks"
    published_date: str = ""
    updated_date: str = ""
    status: str = "draft"
    slug: str = ""
    category_id: str = ""
    category_name: str = ""
    themes: list[str] = None
    tags: list[str] = None
    featured: bool = False
    source_format: str = "paste"
    source_path: str | None = None
    article_relative_path: str | None = None
    canonical_url: str | None = None
    previous_paths: list[str] = None
    redirect_from: list[str] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["themes"] = self.themes or []
        data["tags"] = self.tags or []
        data["previous_paths"] = self.previous_paths or []
        data["redirect_from"] = self.redirect_from or []
        return data


def new_article_id() -> str:
    return str(uuid.uuid4())


def metadata_path_for(article_path: Path) -> Path:
    return article_path.with_suffix(".publisher.json")


def load_metadata(article_path: Path) -> dict | None:
    data = read_json(metadata_path_for(article_path), None)
    if not data:
        return None
    data.setdefault("themes", [])
    data.setdefault("tags", [])
    data.setdefault("previous_paths", [])
    data.setdefault("redirect_from", [])
    return data


def ensure_metadata(article_path: Path, defaults: dict) -> dict:
    existing = load_metadata(article_path)
    if existing:
        return existing
    created = {
        "schema_version": 1,
        "article_id": defaults.get("article_id") or new_article_id(),
        "title": defaults.get("title", ""),
        "english_title": defaults.get("english_title", ""),
        "subtitle": defaults.get("subtitle", ""),
        "summary": defaults.get("summary", ""),
        "author": defaults.get("author", "RedRocks"),
        "published_date": defaults.get("published_date") or today_iso(),
        "updated_date": defaults.get("updated_date") or today_iso(),
        "status": defaults.get("status", "draft"),
        "slug": defaults.get("slug", ""),
        "category_id": defaults.get("category_id", ""),
        "category_name": defaults.get("category_name", ""),
        "themes": defaults.get("themes", []),
        "tags": unique_by_key(defaults.get("tags", [])),
        "featured": bool(defaults.get("featured", False)),
        "source_format": defaults.get("source_format", "paste"),
        "source_path": defaults.get("source_path"),
        "article_relative_path": defaults.get("article_relative_path"),
        "canonical_url": defaults.get("canonical_url"),
        "previous_paths": [],
        "redirect_from": [],
    }
    write_json_atomic(metadata_path_for(article_path), created)
    return created


def save_metadata(article_path: Path, payload: dict) -> None:
    clean = dict(payload)
    clean["themes"] = clean.get("themes") or []
    clean["tags"] = unique_by_key(clean.get("tags") or [])
    clean["previous_paths"] = clean.get("previous_paths") or []
    clean["redirect_from"] = clean.get("redirect_from") or []
    if not clean.get("updated_date"):
        clean["updated_date"] = today_iso()
    write_json_atomic(metadata_path_for(article_path), clean)


def patch_metadata(article_path: Path, **changes) -> dict:
    data = load_metadata(article_path) or {}
    data.update(changes)
    if "tags" in changes:
        data["tags"] = unique_by_key(changes["tags"] or [])
    if "updated_date" not in changes:
        data["updated_date"] = today_iso()
    save_metadata(article_path, data)
    return data

