from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .utils import read_json, write_json_atomic


@dataclass(frozen=True)
class SiteConfig:
    schema_version: int
    site_name: str
    site_base_url: str
    host: str
    port: int
    author_default: str
    article_root: str
    article_index: str
    article_generator: str
    publish_command: str


def load_site_config(root: Path) -> SiteConfig:
    data = read_json(root / "publisher" / "config" / "site.json", {})
    return SiteConfig(**data)


def load_categories(root: Path) -> dict:
    return read_json(root / "publisher" / "config" / "categories.json", {"categories": []})


def load_themes(root: Path) -> dict:
    return read_json(root / "publisher" / "config" / "themes.json", {"themes": []})


def load_tag_registry(root: Path) -> dict:
    path = root / "publisher" / "config" / "tag_registry.json"
    return read_json(path, {"schema_version": 1, "tags": []})


def save_tag_registry(root: Path, payload: dict) -> None:
    write_json_atomic(root / "publisher" / "config" / "tag_registry.json", payload)

