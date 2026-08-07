#!/usr/bin/env python3
"""Backward-compatible HF-only entry point from the old paper-radar skill."""

from __future__ import annotations

import sys

try:
    from .fetch_content import main
except ImportError:  # executed directly as scripts/fetch_papers.py
    from fetch_content import main


def translate_legacy_args(argv: list[str]) -> list[str]:
    translated: list[str] = []
    index = 0
    has_sources = False
    while index < len(argv):
        arg = argv[index]
        if arg == "--keyword-only":
            index += 1
            continue
        if arg == "--base-url":
            translated.append("--hf-base-url")
            if index + 1 < len(argv):
                translated.append(argv[index + 1])
                index += 2
                continue
        elif arg.startswith("--base-url="):
            translated.append("--hf-base-url=" + arg.split("=", 1)[1])
            index += 1
            continue
        if arg == "--sources" or arg.startswith("--sources="):
            has_sources = True
        translated.append(arg)
        index += 1
    if not has_sources:
        translated.extend(["--sources", "hf"])
    return translated


if __name__ == "__main__":
    sys.argv[1:] = translate_legacy_args(sys.argv[1:])
    raise SystemExit(main())
