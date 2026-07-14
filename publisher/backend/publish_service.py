from __future__ import annotations

import shutil
import tempfile
import re
from dataclasses import dataclass
from pathlib import Path

from . import article_service
from .config_service import load_categories, load_site_config
from .git_service import commit, detect_unrelated_changes, head_short_sha, push, stage_files
from .metadata_service import save_metadata
from .utils import copy_file, title_slug, today_iso, write_text_atomic
from .validation_service import normalize_tags, validate_category, validate_title


@dataclass
class PublishResult:
    ok: bool
    message: str
    article_url: str | None = None
    commit: str | None = None
    staged_files: list[str] | None = None
    skipped_push: bool = False
    error_step: str | None = None


def html_to_markdown(html_text: str) -> str:
    cleaned = re.sub(r"<script.*?</script>", "", html_text or "", flags=re.I | re.S)
    cleaned = re.sub(r"\son[a-z]+\s*=\s*(['\"]).*?\1", "", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"javascript:", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip() + "\n"


def prepare_publish(root: Path, payload: dict) -> dict:
    categories = load_categories(root).get("categories", [])
    validate_title(payload.get("title", ""))
    category = validate_category(payload.get("category_id", ""), categories)
    slug = build_publish_slug(root, payload, category["id"])
    article_paths = article_service.article_paths(root, category["id"], slug)
    if article_paths["markdown"].exists() and payload.get("article_id") != (load_metadata(article_paths["markdown"]) or {}).get("article_id"):
        raise ValueError("slug already exists")
    return {
        "category": category,
        "slug": slug,
        "paths": article_paths,
    }


def load_metadata(article_path: Path) -> dict | None:
    from .metadata_service import load_metadata as _load

    return _load(article_path)


def build_publish_slug(root: Path, payload: dict, category_id: str) -> str:
    title = (payload.get("title") or "").strip()
    published_date = (payload.get("published_date") or "").strip() or today_iso()
    date_prefix = re.sub(r"\D+", "", published_date) or re.sub(r"\D+", "", today_iso())
    base = title_slug(title, date_prefix=date_prefix, max_chars=8)
    article_id = payload.get("article_id") or payload.get("metadata", {}).get("article_id")
    candidate = base
    suffix = 2
    while True:
        article_paths = article_service.article_paths(root, category_id, candidate)
        existing_paths = [article_paths["markdown"], article_paths["html"], article_paths["meta"]]
        existing = next((path for path in existing_paths if path.exists()), None)
        if not existing:
            return candidate
        existing_meta = load_metadata(article_paths["markdown"]) or load_metadata(article_paths["html"]) or {}
        if article_id and existing_meta.get("article_id") == article_id:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


def save_article_and_publish(root: Path, payload: dict, git_push: bool = True) -> PublishResult:
    site = load_site_config(root)
    cats = load_categories(root).get("categories", [])
    category = validate_category(payload.get("category_id", ""), cats)
    validate_title(payload.get("title", ""))
    slug = build_publish_slug(root, payload, category["id"])
    title = payload["title"].strip()
    html_body = payload.get("html", "")
    plain_text = payload.get("plain_text", "")
    article_id = payload.get("article_id") or payload.get("metadata", {}).get("article_id")
    article_paths = article_service.article_paths(root, category["id"], slug)

    related_allowed = [
        str(article_paths["markdown"].relative_to(root)),
        str(article_paths["html"].relative_to(root)),
        str(article_paths["meta"].relative_to(root)),
        "articles.html",
        f"articles/{category['directory']}.html",
        "articles/",
        "generate_article.py",
        "publisher/",
        "REDROCKS_PUBLISHER.command",
        ".gitignore",
        "__pycache__/",
    ]

    unrelated = detect_unrelated_changes(root, related_allowed)
    if git_push and unrelated:
        return PublishResult(
            ok=False,
            message="repository has unrelated uncommitted changes",
            error_step="git-preflight",
        )

    article_paths["directory"].mkdir(parents=True, exist_ok=True)
    managed_paths = [
        article_paths["markdown"],
        article_paths["html"],
        article_paths["meta"],
        root / "articles.html",
        root / "articles" / f"{category['directory']}.html",
    ]
    backup_dir = Path(tempfile.mkdtemp(prefix="publisher-backup-", dir=str(root / ".publisher-data" / "temp")))
    backups: dict[Path, Path] = {}
    new_files: list[Path] = []
    cleanup = lambda: shutil.rmtree(backup_dir, ignore_errors=True)

    def backup(path: Path) -> None:
        if path.exists():
            rel = path.relative_to(root)
            target = backup_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            backups[path] = target
        else:
            new_files.append(path)

    def restore() -> None:
        for path in new_files:
            if path.exists():
                path.unlink()
        for original, snapshot in backups.items():
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(snapshot, original)

    for path in managed_paths:
        backup(path)

    metadata = {
        "article_id": article_id or payload.get("metadata", {}).get("article_id"),
        "title": title,
        "english_title": payload.get("english_title", ""),
        "subtitle": payload.get("subtitle", ""),
        "summary": payload.get("summary") or "",
        "author": payload.get("author") or site.author_default,
        "published_date": payload.get("published_date") or payload.get("updated_date") or payload.get("draft_date") or "",
        "updated_date": payload.get("updated_date") or payload.get("published_date") or "",
        "status": "published",
        "slug": slug,
        "category_id": category["id"],
        "category_name": category["name"],
        "themes": payload.get("themes") or [],
        "tags": normalize_tags(payload.get("tags") or []),
        "featured": bool(payload.get("featured", False)),
        "source_format": payload.get("source_format", "paste"),
        "source_path": payload.get("source_path"),
        "article_relative_path": str(article_paths["markdown"].relative_to(root)),
        "canonical_url": f"{site.site_base_url}/articles/{category['directory']}/{slug}.html",
        "previous_paths": payload.get("previous_paths") or [],
        "redirect_from": payload.get("redirect_from") or [],
    }
    if not metadata["article_id"]:
        metadata["article_id"] = article_id or metadata["title"][:8] or slug

    md_text = html_to_markdown(html_body)
    if title and not md_text.lstrip().startswith("# "):
        md_text = f"# {title}\n\n{md_text}".strip() + "\n"

    try:
        write_text_atomic(article_paths["markdown"], md_text)
        save_metadata(article_paths["markdown"], metadata)
        if payload.get("cover_image_path"):
            source = Path(payload["cover_image_path"])
            target = article_paths["directory"] / source.name
            if source.exists() and source.resolve() != target.resolve():
                copy_file(source, target)

        generator = root / site.article_generator
        proc = __import__("subprocess").run(["python3", str(generator)], cwd=str(root), capture_output=True, text=True)
        if proc.returncode != 0:
            restore()
            cleanup()
            return PublishResult(ok=False, message=proc.stderr.strip() or proc.stdout.strip() or "article generation failed", error_step="generate-articles")
    except Exception as exc:
        restore()
        cleanup()
        return PublishResult(ok=False, message=str(exc), error_step="publish-transaction")

    changed = managed_paths

    status = __import__("subprocess").run(["git", "status", "--porcelain"], cwd=str(root), capture_output=True, text=True)
    if status.returncode != 0:
        cleanup()
        return PublishResult(ok=False, message="git status failed", error_step="git-status")

    files = []
    for rel in status.stdout.splitlines():
        path = rel[3:].strip()
        if any(path == p.relative_to(root).as_posix() for p in changed) or path.startswith(f"articles/{category['directory']}/"):
            files.append(path)

    stage_targets = [root / path for path in files if (root / path).exists()]
    if stage_targets:
        rc, stdout, stderr = stage_files(root, stage_targets)
        if rc != 0:
            cleanup()
            return PublishResult(ok=False, message=stderr.strip() or stdout.strip() or "git add failed", error_step="git-add")
        try:
            commit(root, f"Publish article: {title}")
        except Exception as exc:
            cleanup()
            return PublishResult(ok=False, message=str(exc), error_step="git-commit")
        if git_push:
            try:
                push(root)
            except Exception as exc:
                cleanup()
                return PublishResult(
                    ok=False,
                    message=f"saved and committed locally, but push failed: {exc}",
                    article_url=metadata["canonical_url"],
                    commit=head_short_sha(root),
                    staged_files=files,
                    skipped_push=True,
                    error_step="git-push",
                )

    result = PublishResult(
        ok=True,
        message="published",
        article_url=metadata["canonical_url"],
        commit=head_short_sha(root),
        staged_files=files,
        skipped_push=not git_push,
    )
    cleanup()
    return result
