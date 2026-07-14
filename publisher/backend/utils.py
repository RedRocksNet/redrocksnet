from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def today_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.tmp-{uuid.uuid4().hex}"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.tmp-{uuid.uuid4().hex}"
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def safe_slug(value: str) -> str:
    base = re.sub(r"\s+", "-", (value or "").strip().lower())
    base = re.sub(r"[^a-z0-9\u4e00-\u9fff._-]+", "-", base)
    base = re.sub(r"-{2,}", "-", base).strip("-._")
    return base or "untitled"


def title_slug(value: str, date_prefix: str | None = None, max_chars: int = 10) -> str:
    raw = (value or "").strip()
    raw = re.sub(r"[\s_]+", "-", raw)
    raw = re.sub(r"[^\w\u4e00-\u9fff-]+", "", raw)
    raw = re.sub(r"-{2,}", "-", raw).strip("-")
    if not raw:
        raw = "untitled"
    if len(raw) > max_chars:
        raw = raw[:max_chars].rstrip("-")
    if date_prefix:
        date_prefix = re.sub(r"\D+", "", date_prefix)
        if date_prefix:
            return f"{date_prefix}-{raw}"
    return raw


def normalize_tag(value: str) -> str:
    s = re.sub(r"\s+", " ", (value or "").strip())
    if not s:
        return ""
    return s


def tag_key(value: str) -> str:
    return normalize_tag(value).casefold()


def unique_by_key(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        item = normalize_tag(raw)
        if not item:
            continue
        key = tag_key(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def ensure_within_root(root: Path, candidate: Path) -> Path:
    root = root.resolve()
    candidate = candidate.resolve()
    if root == candidate:
        return candidate
    if root not in candidate.parents:
        raise ValueError(f"path escapes repository root: {candidate}")
    return candidate


def run_command(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=False)


def git_output(args: list[str], cwd: Path) -> str:
    proc = run_command(["git", *args], cwd)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "git command failed")
    return proc.stdout.strip()


def markdown_to_plain(md_text: str) -> str:
    s = md_text or ""
    s = re.sub(r"```.*?```", " ", s, flags=re.S)
    s = re.sub(r"`[^`]+`", " ", s)
    s = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", s)
    s = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", s)
    s = re.sub(r"^\s{0,3}#{1,6}\s+", "", s, flags=re.M)
    s = re.sub(r"^\s*>\s?", "", s, flags=re.M)
    s = re.sub(r"^\s*[-*+]\s+", "", s, flags=re.M)
    s = re.sub(r"^\s*\d+\.\s+", "", s, flags=re.M)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def excerpt(text: str, limit: int = 140) -> str:
    plain = markdown_to_plain(text)
    if len(plain) <= limit:
        return plain
    return plain[: limit - 1].rstrip() + "…"


def first_h1(text: str) -> str:
    for line in (text or "").splitlines():
        m = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
    return ""


def strip_first_h1(text: str) -> str:
    lines = (text or "").splitlines()
    out: list[str] = []
    removed = False
    for line in lines:
        if not removed and line.lstrip().startswith("# "):
            removed = True
            continue
        out.append(line)
    return "\n".join(out)


def slugify_title(title: str) -> str:
    base = safe_slug(title)
    if base == "untitled":
        return base
    return base


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
