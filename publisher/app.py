from __future__ import annotations

import base64
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
import sys
import threading
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publisher.backend.article_service import article_paths, load_article_detail, scan_articles
from publisher.backend.config_service import load_categories, load_site_config, load_tag_registry, load_themes, save_tag_registry
from publisher.backend.import_service import import_file_to_html
from publisher.backend.metadata_service import ensure_metadata, load_metadata, patch_metadata
from publisher.backend.git_service import commit as git_commit, push as git_push
from publisher.backend.preview_service import render_article_preview
from publisher.backend.publish_service import save_article_and_publish
from publisher.backend.repository_guard import RepositoryGuardError, ensure_redrocks_repository
from publisher.backend.utils import now_iso, read_json, today_iso, write_json_atomic

DATA_DIR = ROOT / ".publisher-data"
DRAFTS_DIR = DATA_DIR / "drafts"
TEMP_DIR = DATA_DIR / "temp"
LOG_DIR = DATA_DIR / "logs"


def json_response(handler, payload, status=200):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def read_body(handler) -> bytes:
    length = int(handler.headers.get("Content-Length", "0"))
    return handler.rfile.read(length) if length else b""


def read_json_body(handler) -> dict:
    body = read_body(handler)
    if not body:
        return {}
    return json.loads(body.decode("utf-8"))


def ensure_dirs():
    for path in [DATA_DIR, DRAFTS_DIR, TEMP_DIR, LOG_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def load_draft(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_draft(article_id: str, payload: dict) -> Path:
    draft_path = DRAFTS_DIR / f"{article_id}.json"
    write_json_atomic(draft_path, payload)
    return draft_path


def bootstrap_payload(root: Path) -> dict:
    cats = load_categories(root).get("categories", [])
    return {
        "site": load_site_config(root).__dict__,
        "categories": cats,
        "themes": load_themes(root).get("themes", []),
        "tags": load_tag_registry(root).get("tags", []),
        "articles": scan_articles(root),
        "drafts": [load_draft(p) for p in sorted(DRAFTS_DIR.glob("*.json")) if load_draft(p)],
    }


def article_payload_from_state(root: Path, state: dict) -> dict:
    return {
        "article_id": state.get("article_id"),
        "title": state.get("title", ""),
        "english_title": state.get("english_title", ""),
        "subtitle": state.get("subtitle", ""),
        "summary": state.get("summary", ""),
        "author": state.get("author", load_site_config(root).author_default),
        "published_date": state.get("published_date") or today_iso(),
        "updated_date": state.get("updated_date") or today_iso(),
        "status": state.get("status", "draft"),
        "slug": state.get("slug", ""),
        "category_id": state.get("category_id", ""),
        "themes": state.get("themes", []),
        "tags": state.get("tags", []),
        "featured": bool(state.get("featured", False)),
        "html": state.get("html", ""),
        "plain_text": state.get("plain_text", ""),
        "source_format": state.get("source_format", "paste"),
        "source_path": state.get("source_path"),
        "cover_image_path": state.get("cover_image_path"),
        "metadata": state.get("metadata") or {},
    }


def make_preview_html(root: Path, state: dict, mode: str) -> str:
    preview_root = article_payload_from_state(root, state)
    meta = {
        "category_id": preview_root["category_id"],
        "slug": preview_root["slug"] or "preview",
        "title": preview_root["title"] or "预览",
        "summary": preview_root["summary"] or "",
        "published_date": preview_root["published_date"],
        "updated_date": preview_root["updated_date"],
        "canonical_url": preview_root.get("metadata", {}).get("canonical_url"),
    }
    return render_article_preview(root, meta, preview_root["html"], mobile=(mode == "mobile"))


def delete_article_everywhere(root: Path, article_id: str) -> dict:
    detail = load_article_detail(root, article_id)
    if not detail:
        raise FileNotFoundError("article not found")

    family = [
        item
        for item in scan_articles(root)
        if item["category_id"] == detail["category_id"] and item["title"] == detail["title"]
    ]
    if not family:
        family = [detail]

    article_files: set[Path] = set()
    for item in family:
        article_paths_map = article_paths(root, item["category_id"], item["slug"])
        article_files.update([article_paths_map["markdown"], article_paths_map["html"], article_paths_map["meta"]])

        source_path = item.get("source_path")
        if source_path:
            source_candidate = root / source_path
            if source_candidate.exists():
                article_files.add(source_candidate)

        category_dir = root / "articles" / item["category_directory"]
        if category_dir.exists():
            for path in category_dir.iterdir():
                if not path.is_file():
                    continue
                if path.name.startswith("."):
                    continue
                if path.suffix.lower() not in {".md", ".html", ".json", ".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                    continue
                meta = load_metadata(path) or {}
                if path.stem == item["slug"] or meta.get("article_id") == item["article_id"] or meta.get("title") == item["title"]:
                    article_files.add(path)

    article_files = {path for path in article_files if path.exists()}
    backup_root = TEMP_DIR / "delete-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_dir = Path(tempfile.mkdtemp(prefix="publisher-delete-", dir=str(backup_root)))
    backups: dict[Path, Path] = {}

    def backup(path: Path) -> None:
        rel = path.relative_to(root)
        target = backup_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        backups[path] = target

    def restore() -> None:
        for original, snapshot in backups.items():
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(snapshot, original)

    for path in article_files:
        backup(path)

    for path in article_files:
        path.unlink(missing_ok=True)

    generator = root / "generate_article.py"
    proc = subprocess.run(["python3", str(generator)], cwd=str(root), capture_output=True, text=True)
    if proc.returncode != 0:
        restore()
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "article generation failed")

    stage_targets = [
        root / "articles" / detail["category_directory"],
        root / "articles.html",
        root / "articles" / f"{detail['category_directory']}.html",
    ]

    proc = subprocess.run(["git", "add", "-A", "--", *[str(path.relative_to(root)) for path in stage_targets]], cwd=str(root), capture_output=True, text=True)
    if proc.returncode != 0:
        restore()
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "git add failed")

    try:
        git_commit(root, f"Delete article: {detail['title']}")
    except Exception:
        subprocess.run(["git", "restore", "--staged", "--", *[str(path.relative_to(root)) for path in stage_targets]], cwd=str(root), capture_output=True, text=True)
        restore()
        raise

    try:
        git_push(root)
    except Exception:
        raise
    finally:
        shutil.rmtree(backup_dir, ignore_errors=True)

    return detail


class PublisherHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "publisher" / "frontend"), **kwargs)

    def log_message(self, format, *args):
        return

    def _json(self, payload, status=200):
        return json_response(self, payload, status=status)

    def _serve_index(self):
        text = (ROOT / "publisher" / "frontend" / "index.html").read_text(encoding="utf-8")
        body = text.replace("__BOOTSTRAP__", json.dumps(bootstrap_payload(ROOT), ensure_ascii=False))
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self._serve_index()
        if parsed.path == "/app.js":
            return self._serve_frontend_file("app.js")
        if parsed.path == "/styles.css":
            return self._serve_frontend_file("styles.css")
        if parsed.path == "/api/bootstrap":
            return self._json(bootstrap_payload(ROOT))
        if parsed.path == "/api/articles":
            return self._json({"articles": scan_articles(ROOT)})
        if parsed.path.startswith("/api/articles/"):
            article_id = parsed.path.rsplit("/", 1)[-1]
            article = load_article_detail(ROOT, article_id)
            if not article:
                return self._json({"error": "not found"}, status=404)
            return self._json(article)
        if parsed.path.startswith("/api/drafts/"):
            draft_id = parsed.path.rsplit("/", 1)[-1]
            draft = load_draft(DRAFTS_DIR / f"{draft_id}.json")
            if not draft:
                return self._json({"error": "not found"}, status=404)
            return self._json(draft)
        if parsed.path.startswith("/api/preview/"):
            article_id = parsed.path.rsplit("/", 1)[-1]
            draft = load_draft(DRAFTS_DIR / f"{article_id}.json")
            if not draft:
                return self._json({"error": "not found"}, status=404)
            mode = parse_qs(parsed.query).get("mode", ["desktop"])[0]
            html_text = make_preview_html(ROOT, draft, mode)
            data = html_text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        return super().do_GET()

    def _serve_frontend_file(self, filename: str):
        path = ROOT / "publisher" / "frontend" / filename
        if not path.exists():
            return self._json({"error": "not found"}, status=404)
        data = path.read_bytes()
        ctype = "text/javascript; charset=utf-8" if path.suffix == ".js" else "text/css; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/drafts":
                payload = read_json_body(self)
                draft_id = payload.get("article_id") or payload.get("metadata", {}).get("article_id")
                if not draft_id:
                    return self._json({"error": "article_id required"}, status=400)
                payload["updated_at"] = now_iso()
                save_draft(draft_id, payload)
                return self._json({"ok": True, "draft_id": draft_id})
            if parsed.path == "/api/import":
                content_type = self.headers.get("Content-Type", "")
                if "multipart/form-data" not in content_type:
                    return self._json({"error": "multipart form required"}, status=400)
                boundary = content_type.split("boundary=")[-1].encode("utf-8")
                body = read_body(self)
                parts = body.split(b"--" + boundary)
                file_bytes = None
                filename = None
                for part in parts:
                    if b"Content-Disposition" in part and b"filename=" in part:
                        header, _, content = part.partition(b"\r\n\r\n")
                        file_bytes = content.rsplit(b"\r\n", 1)[0]
                        header_text = header.decode("utf-8", "ignore")
                        import re
                        m = re.search(r'filename="([^"]+)"', header_text)
                        filename = m.group(1) if m else "upload"
                        break
                if file_bytes is None:
                    return self._json({"error": "file missing"}, status=400)
                import tempfile
                tmp_dir = TEMP_DIR / "import"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                suffix = Path(filename).suffix.lower()
                tmp_path = tmp_dir / f"import{suffix}"
                tmp_path.write_bytes(file_bytes)
                html_text, plain_text, extracted = import_file_to_html(tmp_path, temp_dir=tmp_dir)
                return self._json(
                    {
                        "html": html_text,
                        "plain_text": plain_text,
                        "title": Path(filename).stem,
                        "extracted_images": [str(p) for p in extracted],
                    }
                )
            if parsed.path == "/api/publish":
                payload = read_json_body(self)
                result = save_article_and_publish(ROOT, payload, git_push=bool(payload.get("git_push", True)))
                return self._json(result.__dict__, status=200 if result.ok else 400)
            if parsed.path == "/api/tags":
                payload = read_json_body(self)
                tag = payload.get("tag", "")
                tag = tag.strip()
                if not tag:
                    return self._json({"error": "tag required"}, status=400)
                registry = load_tag_registry(ROOT)
                existing = registry.get("tags", [])
                existing.append({"name": tag, "key": tag.casefold(), "usage_count": 1})
                seen = {}
                normalized = []
                for item in existing:
                    key = item["key"]
                    seen[key] = seen.get(key, 0) + 1
                    item["usage_count"] = seen[key]
                    if key not in [x["key"] for x in normalized]:
                        normalized.append(item)
                registry["tags"] = normalized
                save_tag_registry(ROOT, registry)
                return self._json({"ok": True, "tag": tag})
        except Exception as exc:
            return self._json({"error": str(exc)}, status=400)
        return self._json({"error": "not found"}, status=404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path.startswith("/api/articles/"):
                article_id = parsed.path.rsplit("/", 1)[-1]
                detail = load_article_detail(ROOT, article_id)
                if not detail:
                    return self._json({"error": "not found"}, status=404)
                deleted = delete_article_everywhere(ROOT, article_id)
                return self._json(
                    {
                        "ok": True,
                        "article_id": article_id,
                        "title": deleted.get("title", ""),
                        "slug": deleted.get("slug", ""),
                        "category_id": deleted.get("category_id", ""),
                    }
                )
        except Exception as exc:
            return self._json({"error": str(exc)}, status=400)
        return self._json({"error": "not found"}, status=404)


def main():
    ensure_dirs()
    context = ensure_redrocks_repository(ROOT)
    host = load_site_config(ROOT).host
    port = load_site_config(ROOT).port
    if host != "127.0.0.1":
        raise SystemExit("Publisher must bind to 127.0.0.1 only")
    print("RedRocks Publisher")
    print(f"Repository: {context.root}")
    print(f"Local address: http://{host}:{port}")
    print("This tool is available only on this Mac.")
    print("Press Control-C to stop.")
    server = ThreadingHTTPServer((host, port), PublisherHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
