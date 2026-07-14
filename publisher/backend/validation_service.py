from __future__ import annotations

import re
from pathlib import Path

from .utils import ensure_within_root, safe_slug, unique_by_key


def validate_title(title: str) -> None:
    if not (title or "").strip():
        raise ValueError("title is required")


def validate_slug(slug: str) -> str:
    clean = safe_slug(slug)
    if not clean:
        raise ValueError("invalid slug")
    if ".." in clean or "/" in clean or "\\" in clean:
        raise ValueError("invalid slug")
    return clean


def validate_category(category_id: str, categories: list[dict]) -> dict:
    for cat in categories:
        if cat["id"] == category_id:
            if not cat.get("enabled", True):
                raise ValueError("category disabled")
            return cat
    raise ValueError("invalid category")


def validate_paths(root: Path, article_path: Path) -> Path:
    return ensure_within_root(root, article_path)


def normalize_tags(tags: list[str]) -> list[str]:
    return unique_by_key(tags)

