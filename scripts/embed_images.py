#!/usr/bin/env python3
"""Embed rendered HTML images as base64 data URIs.

The transformer handles:
- <img src="...">
- SVG <image href="..."> / <image xlink:href="...">
- <source src="..."> / <source srcset="...">
- CSS url(...) values that clearly point to image files

Inline <svg> elements are already self-contained and are left unchanged.
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


QUOTED_IMAGE_RE = re.compile(
    r"""(?is)
    (?P<prefix>
      <img\b[^>]*?\bsrc\s*=\s*
      |
      <image\b[^>]*?\b(?:href|xlink:href)\s*=\s*
    )
    (?P<quote>["'])
    (?P<value>.*?)
    (?P=quote)
    """,
    re.VERBOSE,
)
SOURCE_IMAGE_RE = re.compile(
    r"""(?is)
    (?P<prefix><source\b[^>]*?\b(?P<attr>src|srcset)\s*=\s*)
    (?P<quote>["'])
    (?P<value>.*?)
    (?P=quote)
    """,
    re.VERBOSE,
)
CSS_URL_RE = re.compile(
    r"""(?is)url\(\s*(?P<quote>["']?)(?P<value>.*?)(?P=quote)\s*\)"""
)
IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff",
    ".svg", ".avif",
}


def sniff_mime(data: bytes, source: str) -> str:
    guessed, _ = mimetypes.guess_type(source)
    if guessed and guessed.startswith("image/"):
        return guessed
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    stripped = data.lstrip()
    if stripped.startswith(b"<svg") or (
        stripped.startswith(b"<?xml") and b"<svg" in stripped[:512]
    ):
        return "image/svg+xml"
    raise ValueError(f"cannot determine image MIME type: {source}")


def load_image(value: str, *, html_dir: Path, allow_remote: bool, timeout: int) -> tuple[bytes, str]:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme in {"http", "https"}:
        if not allow_remote:
            raise ValueError(f"remote image disabled: {value}")
        request = urllib.request.Request(value, headers={"User-Agent": "PaperStudio-ImageEmbedder/2.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
            content_type = response.headers.get_content_type()
        mime = content_type if content_type and content_type.startswith("image/") else sniff_mime(data, value)
        return data, mime
    if parsed.scheme == "file":
        path = Path(urllib.request.url2pathname(parsed.path))
    elif parsed.scheme:
        raise ValueError(f"unsupported image URI scheme '{parsed.scheme}': {value}")
    else:
        clean_value = urllib.parse.unquote(value.split("#", 1)[0].split("?", 1)[0])
        path = Path(clean_value)
        if not path.is_absolute():
            path = html_dir / path
    data = path.read_bytes()
    return data, sniff_mime(data, str(path))


def to_data_uri(value: str, *, html_dir: Path, allow_remote: bool, timeout: int) -> str:
    if value.startswith("data:image/") or value.startswith("#"):
        return value
    data, mime = load_image(value, html_dir=html_dir, allow_remote=allow_remote, timeout=timeout)
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def looks_like_css_image(value: str) -> bool:
    if value.startswith(("data:image/", "#")):
        return True
    parsed = urllib.parse.urlparse(value)
    return Path(parsed.path.casefold()).suffix in IMAGE_EXTENSIONS


def embed_html(text: str, *, html_dir: Path, allow_remote: bool = True, timeout: int = 35) -> tuple[str, int]:
    replacements = 0

    def replace_quoted(match: re.Match[str]) -> str:
        nonlocal replacements
        value = match.group("value").strip()
        if not value:
            return match.group(0)
        embedded = to_data_uri(value, html_dir=html_dir, allow_remote=allow_remote, timeout=timeout)
        if embedded != value:
            replacements += 1
        quote = match.group("quote")
        return f"{match.group('prefix')}{quote}{embedded}{quote}"

    text = QUOTED_IMAGE_RE.sub(replace_quoted, text)

    def replace_source(match: re.Match[str]) -> str:
        nonlocal replacements
        value = match.group("value").strip()
        if not value:
            return match.group(0)
        if match.group("attr").casefold() == "src":
            embedded = to_data_uri(
                value,
                html_dir=html_dir,
                allow_remote=allow_remote,
                timeout=timeout,
            )
            if embedded != value:
                replacements += 1
        else:
            candidates = []
            for raw_candidate in value.split(","):
                parts = raw_candidate.strip().split(maxsplit=1)
                if not parts:
                    continue
                embedded_url = to_data_uri(
                    parts[0],
                    html_dir=html_dir,
                    allow_remote=allow_remote,
                    timeout=timeout,
                )
                if embedded_url != parts[0]:
                    replacements += 1
                candidates.append(
                    embedded_url + (f" {parts[1]}" if len(parts) == 2 else "")
                )
            embedded = ", ".join(candidates)
        quote = match.group("quote")
        return f"{match.group('prefix')}{quote}{embedded}{quote}"

    text = SOURCE_IMAGE_RE.sub(replace_source, text)

    def replace_css(match: re.Match[str]) -> str:
        nonlocal replacements
        value = match.group("value").strip()
        if not looks_like_css_image(value):
            return match.group(0)
        embedded = to_data_uri(value, html_dir=html_dir, allow_remote=allow_remote, timeout=timeout)
        if embedded != value:
            replacements += 1
        quote = match.group("quote")
        return f"url({quote}{embedded}{quote})"

    text = CSS_URL_RE.sub(replace_css, text)
    return text, replacements


def main() -> int:
    parser = argparse.ArgumentParser(description="Replace HTML image references with base64 data URIs")
    parser.add_argument("html", help="input HTML")
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument("--in-place", action="store_true")
    output_group.add_argument("-o", "--output")
    parser.add_argument("--no-remote", action="store_true", help="reject http(s) images instead of downloading them")
    parser.add_argument("--timeout", type=int, default=35)
    args = parser.parse_args()

    input_path = Path(args.html).expanduser().resolve()
    output_path = input_path if args.in_place else Path(args.output).expanduser().resolve()
    text = input_path.read_text(encoding="utf-8")
    try:
        embedded, count = embed_html(text, html_dir=input_path.parent, allow_remote=not args.no_remote, timeout=args.timeout)
    except Exception as exc:
        print(f"embed_images: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(embedded, encoding="utf-8")
    print(f"embedded {count} image reference(s) -> {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
