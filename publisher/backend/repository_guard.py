from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .utils import git_output


@dataclass(frozen=True)
class RepositoryContext:
    root: Path
    remote_url: str
    branch: str


class RepositoryGuardError(RuntimeError):
    pass


EXPECTED_FILES = {"index.html", "articles.html", "generate_article.py", "PUBLISH.command", "CNAME"}


def detect_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for candidate in [cur, *cur.parents]:
        if all((candidate / name).exists() for name in EXPECTED_FILES):
            return candidate
    raise RepositoryGuardError(f"not a redrocks.net repository: {start}")


def ensure_redrocks_repository(start: Path) -> RepositoryContext:
    root = detect_repo_root(start)
    remote = git_output(["remote", "-v"], root)
    branch = git_output(["branch", "--show-current"], root)
    if "RedRocksNet/redrocksnet.git" not in remote:
        raise RepositoryGuardError(f"unexpected git remote:\n{remote}")
    return RepositoryContext(root=root, remote_url=remote, branch=branch)

