"""Validate remote/local source links and rebase local links for exported artifacts."""
from html import escape
import os
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlsplit


def source_url(url):
    if not isinstance(url, str) or any(ord(c) < 32 for c in url):
        raise ValueError("来源须为 HTTPS 或安全的相对资料路径")
    parsed = urlsplit(url)
    if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password:
        return url
    decoded = unquote(parsed.path)
    path = PurePosixPath(decoded)
    if (parsed.scheme or parsed.netloc or parsed.query or not decoded or "\\" in decoded or ":" in decoded
            or path.is_absolute() or ".." in path.parts or any(ord(c) < 32 for c in decoded)
            or path.suffix.lower() not in {".pdf", ".html", ".md", ".txt"}):
        raise ValueError("来源须为 HTTPS 或目录内相对 PDF/HTML/Markdown/文本路径")
    return url


def local_sources(value):
    found = set()
    if isinstance(value, dict):
        if isinstance(value.get("url"), str) and not urlsplit(source_url(value["url"])).scheme:
            found.add(value["url"])
        for item in value.values():
            found.update(local_sources(item))
    elif isinstance(value, list):
        for item in value:
            found.update(local_sources(item))
    return found


def rebase_links(markup, urls, input_dir, output_dir):
    base = Path(input_dir).resolve()
    for url in urls:
        parsed = urlsplit(url)
        target = (base / unquote(parsed.path)).resolve()
        if not target.is_relative_to(base) or not target.is_file():
            raise ValueError("本地来源不存在或超出输入目录：" + url)
        relative = quote(Path(os.path.relpath(target, Path(output_dir).resolve())).as_posix(), safe="/-._~")
        if parsed.fragment:
            relative += "#" + parsed.fragment
        markup = markup.replace('href="' + escape(url, quote=True) + '"', 'href="' + escape(relative, quote=True) + '"')
    return markup
