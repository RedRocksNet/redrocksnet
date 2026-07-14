from __future__ import annotations

import base64
import html
import mimetypes
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from .utils import excerpt, normalize_tag, strip_first_h1, unique_by_key


ALLOWED_IMPORT_SUFFIXES = {".txt", ".md", ".docx"}
ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_IMPORT_BYTES = 20 * 1024 * 1024


def clean_text_import(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def txt_to_html(text: str) -> str:
    text = clean_text_import(text)
    blocks = [blk.strip() for blk in re.split(r"\n\s*\n", text) if blk.strip()]
    html_blocks: list[str] = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) == 1 and lines[0].startswith("#"):
            level = len(lines[0]) - len(lines[0].lstrip("#"))
            title = html.escape(lines[0].lstrip("#").strip())
            html_blocks.append(f"<h{max(1, min(level, 6))}>{title}</h{max(1, min(level, 6))}>")
            continue
        if all(re.match(r"^\s*[-*+]\s+", line) for line in lines):
            items = [re.sub(r"^\s*[-*+]\s+", "", line).strip() for line in lines]
            html_blocks.append("<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>")
            continue
        if all(re.match(r"^\s*\d+\.\s+", line) for line in lines):
            items = [re.sub(r"^\s*\d+\.\s+", "", line).strip() for line in lines]
            html_blocks.append("<ol>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ol>")
            continue
        if block.startswith(">"):
            quote = "\n".join(re.sub(r"^\s*>\s?", "", line) for line in lines)
            html_blocks.append(f"<blockquote><p>{html.escape(quote).replace(chr(10), '<br>')}</p></blockquote>")
            continue
        html_blocks.append(f"<p>{html.escape(block).replace(chr(10), '<br>')}</p>")
    return "\n".join(html_blocks)


def md_to_html(text: str) -> str:
    import markdown

    return markdown.markdown(strip_first_h1(clean_text_import(text)), extensions=["extra", "tables", "fenced_code"])


def _docx_ns() -> dict[str, str]:
    return {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
        "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    }


def docx_to_html(docx_path: Path, temp_dir: Path | None = None) -> tuple[str, list[Path]]:
    ns = _docx_ns()
    extracted: list[Path] = []
    with zipfile.ZipFile(docx_path) as zf:
        doc_xml = zf.read("word/document.xml")
        root = ET.fromstring(doc_xml)
        rels = {}
        try:
            rels_xml = zf.read("word/_rels/document.xml.rels")
            rels_root = ET.fromstring(rels_xml)
            for rel in rels_root:
                rels[rel.attrib.get("Id")] = rel.attrib.get("Target")
        except KeyError:
            pass

        paragraphs: list[str] = []
        current_list: list[str] = []

        def flush_list() -> None:
            nonlocal current_list
            if current_list:
                paragraphs.append("<ul>" + "".join(current_list) + "</ul>")
                current_list = []

        for p in root.iterfind(".//w:body/w:p", ns):
            texts: list[str] = []
            runs: list[str] = []
            p_style = ""
            ppr = p.find("w:pPr", ns)
            if ppr is not None:
                pstyle = ppr.find("w:pStyle", ns)
                if pstyle is not None:
                    p_style = pstyle.attrib.get(f"{{{ns['w']}}}val", "")

            for node in p.iter():
                tag = node.tag
                if tag.endswith("}t") and node.text:
                    texts.append(html.escape(node.text))
                elif tag.endswith("}br"):
                    texts.append("<br>")
                elif tag.endswith("}tab"):
                    texts.append("&emsp;")
                elif tag.endswith("}blip"):
                    rid = node.attrib.get(f"{{{ns['r']}}}embed")
                    target = rels.get(rid)
                    if target and target.startswith("media/") and temp_dir:
                        media_path = Path(target)
                        with zf.open(f"word/{target}") as fh:
                            data = fh.read()
                        suffix = Path(target).suffix or ".png"
                        out = temp_dir / f"docx-image-{len(extracted)+1}{suffix}"
                        out.parent.mkdir(parents=True, exist_ok=True)
                        out.write_bytes(data)
                        extracted.append(out)
                        mime = mimetypes.guess_type(str(out))[0] or "application/octet-stream"
                        b64 = base64.b64encode(data).decode("ascii")
                        texts.append(f'<img src="data:{mime};base64,{b64}" alt="docx image" />')

            text = "".join(texts).strip()
            if not text:
                flush_list()
                continue
            if p_style.lower().startswith("list"):
                current_list.append(f"<li>{text}</li>")
                continue
            flush_list()
            if p_style.lower().startswith("heading"):
                m = re.search(r"(\d+)$", p_style)
                level = int(m.group(1)) if m else 1
                paragraphs.append(f"<h{max(1, min(level, 6))}>{text}</h{max(1, min(level, 6))}>")
            else:
                paragraphs.append(f"<p>{text}</p>")

        flush_list()
        return "\n".join(paragraphs), extracted


def import_file_to_html(path: Path, temp_dir: Path | None = None) -> tuple[str, str, list[Path]]:
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_IMPORT_SUFFIXES:
        raise ValueError("unsupported file type")
    if path.stat().st_size > MAX_IMPORT_BYTES:
        raise ValueError("file too large")
    if suffix == ".txt":
        text = path.read_text(encoding="utf-8", errors="replace")
        return txt_to_html(text), clean_text_import(text), []
    if suffix == ".md":
        text = path.read_text(encoding="utf-8", errors="replace")
        return md_to_html(text), clean_text_import(text), []
    html_text, images = docx_to_html(path, temp_dir=temp_dir)
    plain = re.sub(r"<[^>]+>", " ", html_text)
    plain = re.sub(r"\s+", " ", plain).strip()
    return html_text, plain, images

