from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from publisher.backend import repository_guard
from publisher.backend.import_service import clean_text_import, import_file_to_html
from publisher.backend.utils import normalize_tag, safe_slug, title_slug, unique_by_key
from publisher.backend.validation_service import validate_slug


ROOT = Path(__file__).resolve().parents[2]


class CoreTests(unittest.TestCase):
    def test_repository_guard(self):
        ctx = repository_guard.ensure_redrocks_repository(ROOT)
        self.assertEqual(ctx.root, ROOT)
        self.assertIn("redrocksnet.git", ctx.remote_url)

    def test_slug_validation(self):
        self.assertEqual(validate_slug("Hello World"), "hello-world")
        self.assertEqual(safe_slug("中文 标题"), "中文-标题")
        self.assertEqual(title_slug("知识、理解与智慧——从一个玩笑开始", date_prefix="20260714", max_chars=7), "20260714-知识理解与智慧")
        self.assertEqual(title_slug("  ", date_prefix="20260714"), "20260714-untitled")

    def test_tag_normalization(self):
        self.assertEqual(unique_by_key(["A", "a", "  A  ", "中文"]), ["A", "中文"])
        self.assertEqual(normalize_tag("  hello   world "), "hello world")

    def test_txt_import(self):
        text = clean_text_import("Title\n\nParagraph")
        self.assertIn("Paragraph", text)

    def test_docx_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.docx"
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr(
                    "word/document.xml",
                    """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                      <w:body>
                        <w:p><w:r><w:t>Hello DOCX</w:t></w:r></w:p>
                        <w:sectPr />
                      </w:body>
                    </w:document>""",
                )
                zf.writestr(
                    "[Content_Types].xml",
                    """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                      <Default Extension="xml" ContentType="application/xml"/>
                    </Types>""",
                )
            html_text, plain, extracted = import_file_to_html(path, temp_dir=Path(tmp))
            self.assertIn("Hello DOCX", html_text)
            self.assertIn("Hello DOCX", plain)
            self.assertEqual(extracted, [])


if __name__ == "__main__":
    unittest.main()
