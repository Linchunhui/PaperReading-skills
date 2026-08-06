#!/usr/bin/env python3
"""Validate PaperStudio's deterministic HTML delivery rules."""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.parse
from pathlib import Path


IMG_SRC_RE = re.compile(
    r"""(?is)<img\b[^>]*?\bsrc\s*=\s*(?P<quote>["'])(?P<value>.*?)(?P=quote)"""
)
SVG_IMAGE_RE = re.compile(
    r"""(?is)<image\b[^>]*?\b(?:href|xlink:href)\s*=\s*(?P<quote>["'])(?P<value>.*?)(?P=quote)"""
)
SOURCE_SRC_RE = re.compile(
    r"""(?is)<source\b[^>]*?\b(?P<attr>src|srcset)\s*=\s*(?P<quote>["'])(?P<value>.*?)(?P=quote)"""
)
DATA_SRCSET_ITEM_RE = re.compile(
    r"""data:image/[^;,\s]+;base64,[A-Za-z0-9+/=]+(?:\s+(?:\d+(?:\.\d+)?[wx]))?""",
    re.IGNORECASE,
)
CSS_URL_RE = re.compile(
    r"""(?is)url\(\s*(?P<quote>["']?)(?P<value>.*?)(?P=quote)\s*\)"""
)
IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif",
    ".tiff", ".svg", ".avif",
}


def validate_data_uri(value: str) -> str | None:
    if not value.startswith("data:image/"):
        return "not a data:image URI"
    marker = ";base64,"
    if marker not in value:
        return "image data URI is not base64 encoded"
    encoded = value.split(marker, 1)[1]
    try:
        base64.b64decode(encoded, validate=True)
    except Exception as exc:
        return f"invalid base64 payload: {exc}"
    return None


def is_css_image(value: str) -> bool:
    if value.startswith("data:image/"):
        return True
    path = urllib.parse.urlparse(value).path.casefold()
    return Path(path).suffix in IMAGE_EXTENSIONS


def validate_srcset(value: str) -> list[str]:
    errors: list[str] = []
    matches = list(DATA_SRCSET_ITEM_RE.finditer(value))
    if not matches:
        return ["srcset contains no base64 data:image item"]
    remainder_parts = []
    cursor = 0
    for match in matches:
        remainder_parts.append(value[cursor:match.start()])
        candidate = match.group(0).split(maxsplit=1)[0]
        problem = validate_data_uri(candidate)
        if problem:
            errors.append(problem)
        cursor = match.end()
    remainder_parts.append(value[cursor:])
    remainder = "".join(remainder_parts).replace(",", "").strip()
    if remainder:
        errors.append(f"srcset contains an external or malformed item: {remainder[:120]}")
    return errors


def validate_html(
    html_path: Path,
    *,
    source_pdf: Path | None = None,
) -> dict[str, object]:
    text = html_path.read_text(encoding="utf-8")
    errors: list[str] = []
    checked_images = 0

    if html_path.suffix != ".html":
        errors.append(f"output extension must be '.html': {html_path.name}")

    if source_pdf:
        expected_html = source_pdf.with_suffix(".html")
        if html_path != expected_html:
            errors.append(
                "filename/location mismatch: "
                f"expected '{expected_html}', got '{html_path}'"
            )

    for label, pattern in (
        ("img src", IMG_SRC_RE),
        ("svg image href", SVG_IMAGE_RE),
    ):
        for match in pattern.finditer(text):
            value = match.group("value").strip()
            if label == "svg image href" and value.startswith("#"):
                continue
            checked_images += 1
            problem = validate_data_uri(value)
            if problem:
                errors.append(f"{label}: {problem}: {value[:120]}")

    for match in SOURCE_SRC_RE.finditer(text):
        value = match.group("value").strip()
        if match.group("attr").casefold() == "srcset":
            problems = validate_srcset(value)
            checked_images += max(1, len(DATA_SRCSET_ITEM_RE.findall(value)))
            for problem in problems:
                errors.append(f"picture/source srcset: {problem}: {value[:120]}")
        else:
            checked_images += 1
            problem = validate_data_uri(value)
            if problem:
                errors.append(f"picture/source src: {problem}: {value[:120]}")

    for match in CSS_URL_RE.finditer(text):
        value = match.group("value").strip()
        if value.startswith("#") or not is_css_image(value):
            continue
        checked_images += 1
        problem = validate_data_uri(value)
        if problem:
            errors.append(f"CSS image url: {problem}: {value[:120]}")

    return {
        "html": str(html_path),
        "source_pdf": str(source_pdf) if source_pdf else "",
        "checked_images": checked_images,
        "ok": not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate PaperStudio HTML filename and base64 image rules"
    )
    parser.add_argument("html")
    parser.add_argument("--source-pdf")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    html_path = Path(args.html).expanduser().resolve()
    source_pdf = (
        Path(args.source_pdf).expanduser().resolve()
        if args.source_pdf
        else None
    )
    report = validate_html(html_path, source_pdf=source_pdf)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report["ok"]:
        print(
            f"OK: {html_path.name}; checked {report['checked_images']} embedded image(s)"
        )
    else:
        print(f"FAIL: {html_path}", file=sys.stderr)
        for error in report["errors"]:
            print(f"- {error}", file=sys.stderr)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
