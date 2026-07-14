from __future__ import annotations

import subprocess
from pathlib import Path

from .utils import git_output, run_command


def repo_status_porcelain(root: Path) -> list[str]:
    proc = run_command(["git", "status", "--porcelain=v1", "-z"], root)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "git status failed")
    parts = proc.stdout.split("\0")
    lines: list[str] = []
    i = 0
    while i < len(parts):
      entry = parts[i]
      if not entry:
        i += 1
        continue
      if len(entry) < 3:
        i += 1
        continue
      status = entry[:2]
      path = entry[3:] if len(entry) > 3 else ""
      if status[0] in {"R", "C"} and i + 1 < len(parts) and parts[i + 1]:
        path = parts[i + 1]
        i += 1
      lines.append(f"{status} {path}")
      i += 1
    return lines


def has_uncommitted_changes(root: Path) -> bool:
    return bool(repo_status_porcelain(root))


def detect_unrelated_changes(root: Path, allowed_paths: list[str]) -> list[str]:
    allowed = []
    for path in allowed_paths:
        item = str(path).replace("\\", "/")
        if item.startswith("./"):
            item = item[2:]
        allowed.append(item)
    unrelated: list[str] = []

    def is_allowed(path: str) -> bool:
        for item in allowed:
            if not item:
                continue
            item = item.rstrip("/")
            if path == item:
                return True
            if path.startswith(item + "/"):
                return True
        return False

    for line in repo_status_porcelain(root):
        path = line[3:].strip()
        if not is_allowed(path):
            unrelated.append(path)
    return unrelated


def stage_files(root: Path, paths: list[Path]) -> tuple[int, str, str]:
    rels = [str(path.relative_to(root)) for path in paths]
    proc = run_command(["git", "add", "--", *rels], root)
    return proc.returncode, proc.stdout, proc.stderr


def commit(root: Path, message: str) -> str:
    proc = run_command(["git", "commit", "-m", message], root)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "git commit failed")
    return proc.stdout.strip()


def push(root: Path) -> str:
    proc = run_command(["git", "push"], root)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "git push failed")
    return proc.stdout.strip()


def head_short_sha(root: Path) -> str:
    return git_output(["rev-parse", "--short", "HEAD"], root)
