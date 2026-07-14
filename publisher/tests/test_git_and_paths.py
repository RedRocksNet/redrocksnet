from __future__ import annotations

import unittest
from pathlib import Path

from publisher.backend.repository_guard import ensure_redrocks_repository
from publisher.backend.git_service import detect_unrelated_changes
from publisher.backend.utils import ensure_within_root


ROOT = Path(__file__).resolve().parents[2]


class GitAndPathTests(unittest.TestCase):
    def test_path_guard(self):
        root = Path("/tmp/root").resolve()
        with self.assertRaises(ValueError):
            ensure_within_root(root, Path("/tmp/other/file.txt"))

    def test_detect_unrelated_changes(self):
        ctx = ensure_redrocks_repository(ROOT)
        result = detect_unrelated_changes(ctx.root, [])
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
