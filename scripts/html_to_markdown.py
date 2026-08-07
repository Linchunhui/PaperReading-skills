#!/usr/bin/env python3
"""Convert PaperStudio HTML into a portable WeChat-oriented Markdown draft.

The converter is deterministic: it removes navigation-heavy sections, extracts
base64 images and inline SVGs, converts common HTML blocks to Markdown, and
moves links to a reference list. Semantic shortening remains the agent's job.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html as html_lib
import re
import sys
from collections import OrderedDict
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


DATA_URI_RE = re.compile(
    r"^data:(?P<mime>image/[a-z0-9.+-]+);base64,(?P<data>[A-Za-z0-9+/=\s]+)$",
    re.IGNORECASE,
)
INLINE_SVG_RE = re.compile(r"(?is)<svg\b.*?</svg>")
SPACE_RE = re.compile(r"[ \t\r\f\v]+")
BLANK_RE = re.compile(r"\n{3,}")
DROP_IDS = {"toc", "qa", "quotes", "inspiration"}
SKIP_TAGS = {"head", "style", "script", "noscript", "nav"}
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
MIME_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/avif": ".avif",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
}


def attr_map(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {key.casefold(): value or "" for key, value in attrs}


class AssetManager:
    def __init__(self, directory: Path, markdown_parent: Path, enabled: bool = True):
        self.directory = directory
        self.markdown_parent = markdown_parent
        self.enabled = enabled
        self._seen: dict[str, Path] = {}
        self._counter = 0

    def _relative(self, path: Path) -> str:
        try:
            return path.relative_to(self.markdown_parent).as_posix()
        except ValueError:
            return path.as_posix()

    def save_bytes(self, data: bytes, suffix: str) -> str:
        digest = hashlib.sha256(data).hexdigest()
        if digest in self._seen:
            return self._relative(self._seen[digest])
        self._counter += 1
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"image-{self._counter:02d}{suffix}"
        path.write_bytes(data)
        self._seen[digest] = path
        return self._relative(path)

    def materialize(self, src: str) -> str:
        match = DATA_URI_RE.match(src.strip())
        if not match or not self.enabled:
            return src
        try:
            data = base64.b64decode(match.group("data"), validate=False)
        except Exception as exc:
            raise ValueError(f"invalid base64 image: {exc}") from exc
        mime = match.group("mime").casefold()
        suffix = MIME_EXTENSIONS.get(mime, ".img")
        return self.save_bytes(data, suffix)


def replace_inline_svgs(text: str, assets: AssetManager) -> str:
    def replace(match: re.Match[str]) -> str:
        svg = match.group(0)
        if not assets.enabled:
            return '<p class="svg-placeholder">[SVG 图表请在发布前转为 PNG]</p>'
        src = assets.save_bytes(svg.encode("utf-8"), ".svg")
        return f'<img src="{html_lib.escape(src, quote=True)}" alt="论文图表">'

    return INLINE_SVG_RE.sub(replace, text)


class PaperMarkdownParser(HTMLParser):
    def __init__(self, *, compact: bool, assets: AssetManager, keep_qa: bool):
        super().__init__(convert_charrefs=True)
        self.compact = compact
        self.assets = assets
        self.keep_qa = keep_qa
        self.parts: list[str] = []
        self.skip_depth = 0
        self.skip_tags: list[str] = []
        self.list_stack: list[dict[str, int | str]] = []
        self.link_stack: list[str] = []
        self.references: OrderedDict[str, int] = OrderedDict()
        self.in_pre = False
        self.in_code = False
        self.blockquote_depth = 0
        self.in_table = False
        self.table_rows: list[list[str]] = []
        self.current_row: list[str] | None = None
        self.current_cell: list[str] | None = None

    def emit(self, value: str) -> None:
        if value:
            self.parts.append(value)

    def block(self, value: str = "") -> None:
        self.emit("\n\n")
        self.emit(value)

    def _must_skip(self, tag: str, attrs: dict[str, str]) -> bool:
        if tag in SKIP_TAGS:
            return True
        if tag == "aside" and attrs.get("id", "").casefold() == "toc":
            return True
        if self.compact and tag in {"details"} and not self.keep_qa:
            return True
        if self.compact and attrs.get("id", "").casefold() in DROP_IDS:
            if attrs.get("id", "").casefold() == "qa" and self.keep_qa:
                return False
            return True
        return False

    def handle_starttag(self, tag: str, attrs_raw: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        attrs = attr_map(attrs_raw)
        if self.skip_depth:
            if tag not in VOID_TAGS:
                self.skip_depth += 1
                self.skip_tags.append(tag)
            return
        if self._must_skip(tag, attrs):
            self.skip_depth = 1
            self.skip_tags = [tag]
            return

        if self.in_table and tag not in {"table", "tr", "td", "th"}:
            return

        if tag in {"h1", "h2", "h3", "h4"}:
            level = int(tag[1])
            if self.compact:
                level = min(level, 3)
            self.block("#" * level + " ")
        elif tag == "p":
            self.block()
        elif tag == "br":
            self.emit("  \n")
        elif tag == "hr":
            self.block("---")
        elif tag in {"strong", "b"}:
            self.emit("**")
        elif tag in {"em", "i"}:
            self.emit("*")
        elif tag == "code" and not self.in_pre:
            self.in_code = True
            self.emit("`")
        elif tag == "pre":
            self.in_pre = True
            self.block("```\n")
        elif tag == "blockquote":
            self.blockquote_depth += 1
            self.block("> ")
        elif tag in {"ul", "ol"}:
            self.list_stack.append({"type": tag, "index": 0})
            self.block()
        elif tag == "li":
            depth = max(0, len(self.list_stack) - 1)
            prefix = "- "
            if self.list_stack and self.list_stack[-1]["type"] == "ol":
                self.list_stack[-1]["index"] = int(self.list_stack[-1]["index"]) + 1
                prefix = f"{self.list_stack[-1]['index']}. "
            self.emit("\n" + "  " * depth + prefix)
        elif tag == "a":
            href = attrs.get("href", "").strip()
            self.link_stack.append(href)
            if not self.compact and href:
                self.emit("[")
        elif tag == "img":
            src = attrs.get("src", "").strip()
            alt = attrs.get("alt", "图片").strip() or "图片"
            if src:
                src = self.assets.materialize(src)
                self.block(f"![{alt}]({src})")
        elif tag == "figcaption":
            self.block("*图注：")
        elif tag == "summary":
            self.block("**")
        elif tag == "table":
            self.in_table = True
            self.table_rows = []
        elif tag == "tr" and self.in_table:
            self.current_row = []
        elif tag in {"td", "th"} and self.in_table:
            self.current_cell = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if self.skip_depth:
            self.skip_depth -= 1
            if self.skip_tags:
                self.skip_tags.pop()
            return


        if self.in_table and tag not in {"table", "tr", "td", "th"}:
            return

        if tag in {"strong", "b"}:
            self.emit("**")
        elif tag in {"em", "i"}:
            self.emit("*")
        elif tag == "code" and self.in_code:
            self.emit("`")
            self.in_code = False
        elif tag == "pre" and self.in_pre:
            self.emit("\n```")
            self.in_pre = False
            self.block()
        elif tag == "blockquote":
            self.blockquote_depth = max(0, self.blockquote_depth - 1)
            self.block()
        elif tag in {"ul", "ol"}:
            if self.list_stack:
                self.list_stack.pop()
            self.block()
        elif tag == "a":
            href = self.link_stack.pop() if self.link_stack else ""
            if href:
                if self.compact:
                    number = self.references.setdefault(href, len(self.references) + 1)
                    self.emit(f"[{number}]")
                else:
                    self.emit(f"]({href})")
        elif tag == "figcaption":
            self.emit("*")
        elif tag == "summary":
            self.emit("**")
        elif tag in {"td", "th"} and self.in_table:
            if self.current_row is not None and self.current_cell is not None:
                cell = SPACE_RE.sub(" ", "".join(self.current_cell)).strip()
                self.current_row.append(cell)
            self.current_cell = None
        elif tag == "tr" and self.in_table:
            if self.current_row:
                self.table_rows.append(self.current_row)
            self.current_row = None
        elif tag == "table" and self.in_table:
            self._emit_table()
            self.in_table = False

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        if self.in_pre:
            self.emit(data)
            return
        value = SPACE_RE.sub(" ", data)
        if self.current_cell is not None:
            self.current_cell.append(value)
        else:
            self.emit(value)

    def _emit_table(self) -> None:
        rows = [row for row in self.table_rows if row]
        if not rows:
            return
        if self.compact:
            self.block()
            for row in rows:
                label = row[0]
                rest = "；".join(cell for cell in row[1:] if cell)
                if rest:
                    self.emit(f"\n- **{label}**：{rest}")
                else:
                    self.emit(f"\n- {label}")
            self.block()
            return
        width = max(len(row) for row in rows)
        normalized = [row + [""] * (width - len(row)) for row in rows]
        self.block("| " + " | ".join(normalized[0]) + " |\n")
        self.emit("| " + " | ".join(["---"] * width) + " |\n")
        for row in normalized[1:]:
            self.emit("| " + " | ".join(row) + " |\n")

    def markdown(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = BLANK_RE.sub("\n\n", text).strip()
        if self.compact and self.references:
            text += "\n\n## 参考资料\n\n"
            for href, number in self.references.items():
                text += f"[{number}] {href}\n"
        return text.strip() + "\n"


def compact_at_blocks(markdown: str, max_chars: int) -> str:
    if max_chars <= 0 or len(markdown) <= max_chars:
        return markdown
    reference_marker = "\n## 参考资料\n"
    body, marker, references = markdown.partition(reference_marker)
    budget = max_chars - (len(marker) + len(references) if marker else 0) - 20
    kept: list[str] = []
    size = 0
    for block in body.split("\n\n"):
        added = len(block) + (2 if kept else 0)
        if kept and size + added > max(300, budget):
            break
        kept.append(block)
        size += added
    result = "\n\n".join(kept).rstrip() + "\n\n> 本文已按长度上限截取，请在发布前做一次语义精简与结尾检查。\n"
    if marker:
        result += marker + references
    return result


def convert_html(
    html_path: Path,
    output_path: Path,
    *,
    compact: bool,
    max_chars: int,
    extract_images: bool,
    assets_dir: Path,
    keep_qa: bool,
) -> tuple[str, int]:
    assets = AssetManager(assets_dir, output_path.parent, enabled=extract_images)
    source = html_path.read_text(encoding="utf-8")
    source = replace_inline_svgs(source, assets)
    parser = PaperMarkdownParser(compact=compact, assets=assets, keep_qa=keep_qa)
    parser.feed(source)
    markdown = parser.markdown()
    markdown = compact_at_blocks(markdown, max_chars)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return markdown, assets._counter


def default_output(html_path: Path) -> Path:
    return html_path.with_name(f"{html_path.stem}.wechat.md")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert PaperStudio HTML to WeChat-oriented Markdown"
    )
    parser.add_argument("html", help="source HTML file")
    parser.add_argument("-o", "--output", help="output Markdown; default: {stem}.wechat.md")
    parser.add_argument(
        "--compact",
        action="store_true",
        help="drop navigation/optional sections, simplify tables, and use numbered references",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=0,
        help="optional hard character ceiling applied at Markdown block boundaries",
    )
    parser.add_argument("--assets-dir", help="directory for extracted base64 images and SVGs")
    parser.add_argument("--no-extract-images", action="store_true")
    parser.add_argument("--keep-qa", action="store_true")
    args = parser.parse_args()

    html_path = Path(args.html).expanduser().resolve()
    if not html_path.is_file():
        print(f"html_to_markdown: file not found: {html_path}", file=sys.stderr)
        return 1
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else default_output(html_path)
    )
    assets_dir = (
        Path(args.assets_dir).expanduser().resolve()
        if args.assets_dir
        else output_path.parent / f"{html_path.stem}.wechat-assets"
    )
    try:
        markdown, image_count = convert_html(
            html_path,
            output_path,
            compact=args.compact,
            max_chars=args.max_chars,
            extract_images=not args.no_extract_images,
            assets_dir=assets_dir,
            keep_qa=args.keep_qa,
        )
    except Exception as exc:
        print(f"html_to_markdown: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(
        f"wrote {len(markdown)} chars, extracted {image_count} image(s) -> {output_path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
