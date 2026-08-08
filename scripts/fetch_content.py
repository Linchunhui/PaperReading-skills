#!/usr/bin/env python3
"""PaperStudio radar fetcher.

Collect research papers and AI-media articles from multiple sources, normalize
them into one JSON schema, keyword-prefilter by research direction, and dedupe
cross-source coverage. The semantic keep/drop decision remains the skill's job.

The script intentionally uses only Python's standard library so it can run from
Codex automations or cron without installing dependencies.
"""

from __future__ import annotations

import argparse
import copy
import email.utils
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable


HF_DEFAULT_BASE = "https://huggingface.co"
HF_API_PATH = "/api/daily_papers"
ARXIV_API = "https://export.arxiv.org/api/query"
QBITAI_RSS = "https://www.qbitai.com/feed"

ARXIV_CATEGORIES = ("cs.CV", "cs.CL", "cs.LG", "cs.AI", "cs.RO", "cs.IR")

# High-recall keyword layer. references/directions.md is the semantic boundary.
DIRECTIONS: dict[str, dict[str, Any]] = {
    "diffusion_llm": {
        "label": "Diffusion LLM",
        "keywords": (
            "diffusion language", "diffusion lm", "diffusion llm",
            "masked diffusion", "language diffusion", "text diffusion",
            "llada", "diffusion tokenizer",
        ),
    },
    "multimodal": {
        "label": "多模态 / VLM",
        "keywords": (
            "multimodal", "multi-modal", "vision-language", "vision language",
            "vlm", "mllm", "omnimodal", "any-to-any", "unified multimodal",
            "视觉语言", "多模态", "视觉大模型",
        ),
    },
    "vla": {
        "label": "VLA",
        "keywords": (
            "vision-language-action", "vision language action", "vla",
            "robot policy", "generalist robot", "embodied", "manipulation",
            "robotic", "humanoid", "具身智能", "机器人策略", "视觉语言动作",
        ),
    },
    "ocr": {
        "label": "OCR / 文档理解",
        "keywords": (
            "ocr", "optical character", "document understanding",
            "document parsing", "document ai", "document image",
            "scene text", "table recognition", "formula recognition",
            "文档解析", "文档理解", "文字识别", "版面分析", "表格识别",
        ),
    },
    "rl": {
        "label": "RL",
        "keywords": (
            "reinforcement learning", "rlhf", "rlvr", "grpo", "ppo",
            "reward model", "reward modeling", "policy gradient", "self-play",
            "inference-time rl", "强化学习", "奖励模型", "自博弈",
        ),
    },
    "world_model": {
        "label": "世界模型",
        "keywords": (
            "world model", "world simulator", "world-model", "world dynamics",
            "interactive world", "action-conditioned video", "dreamer",
            "世界模型", "世界模拟器", "环境动态", "交互世界",
        ),
    },
    "foundation_model": {
        "label": "基座模型 / LLM",
        "keywords": (
            "foundation model", "base model", "large language model",
            "language model pretraining", "llm pretraining", "reasoning model",
            "mixture of experts", "scaling law", "model architecture",
            "基座模型", "基础模型", "大语言模型", "预训练", "推理模型",
            "混合专家", "moe", "scaling",
        ),
    },
}

WORD_RE = re.compile(r"[\W_]+", re.UNICODE)
ARXIV_ID_RE = re.compile(
    r"(?:arxiv(?:\.org)?[/:]\s*)?(?P<id>\d{4}\.\d{4,5})(?:v\d+)?",
    re.IGNORECASE,
)


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def daterange(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def resolve_range(
    range_name: str | None,
    one_date: str | None,
    start_text: str | None,
    end_text: str | None,
) -> tuple[date, date]:
    today = date.today()
    if one_date:
        value = date.fromisoformat(one_date)
        return value, value
    if start_text:
        if not end_text:
            raise ValueError("--start requires --end")
        return date.fromisoformat(start_text), date.fromisoformat(end_text)
    if range_name in (None, "today"):
        return today, today
    if range_name == "week":
        return today - timedelta(days=today.weekday()), today
    if range_name == "month":
        return today.replace(day=1), today
    raise ValueError(f"unsupported range: {range_name}")


def http_get(url: str, timeout: int = 35) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PaperStudio-Radar/2.0 (+local research digest)",
            "Accept": "application/json, application/atom+xml, application/rss+xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def clip(value: str, limit: int) -> str:
    value = value.strip()
    if limit <= 0 or len(value) <= limit:
        return value
    return value[:limit].rstrip() + "…"


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        if parsed:
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    normalized = raw.replace("Z", "+00:00").replace("/", "-")
    for candidate in (normalized, normalized.replace(" ", "T")):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def iso_datetime(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def in_period(value: datetime | None, start: date, end: date) -> bool:
    if value is None:
        return False
    local_day = value.astimezone().date()
    return start <= local_day <= end


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def child_text(element: ET.Element, names: tuple[str, ...]) -> str:
    wanted = {name.lower() for name in names}
    for child in element:
        if local_name(child.tag) in wanted:
            return "".join(child.itertext()).strip()
    return ""


def extract_arxiv_id(*values: str) -> str:
    for value in values:
        match = ARXIV_ID_RE.search(value or "")
        if match:
            return match.group("id")
    return ""


def compile_matchers() -> dict[str, re.Pattern[str]]:
    matchers: dict[str, re.Pattern[str]] = {}
    for key, config in DIRECTIONS.items():
        parts = []
        for keyword in config["keywords"]:
            escaped = re.escape(keyword.casefold())
            if re.fullmatch(r"[a-z0-9_-]+", keyword.casefold()):
                parts.append(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")
            else:
                parts.append(escaped)
        matchers[key] = re.compile("|".join(parts), re.IGNORECASE)
    return matchers


def tag_directions(item: dict[str, Any], matchers: dict[str, re.Pattern[str]]) -> list[str]:
    haystack = " ".join(
        str(item.get(field, ""))
        for field in ("title", "summary", "content", "tags")
    ).casefold()
    return [key for key, matcher in matchers.items() if matcher.search(haystack)]


def make_item(
    *,
    source: str,
    source_type: str,
    kind: str,
    title: str,
    summary: str = "",
    content: str = "",
    url: str = "",
    pdf_url: str = "",
    published_at: datetime | None = None,
    authors: list[str] | None = None,
    score: int = 0,
    arxiv_id: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": arxiv_id or url or title,
        "kind": kind,
        "source": source,
        "source_type": source_type,
        "title": strip_html(title),
        "summary": strip_html(summary),
        "content": strip_html(content),
        "url": url,
        "pdf_url": pdf_url,
        "published_at": iso_datetime(published_at),
        "authors": authors or [],
        "score": int(score or 0),
        "arxiv_id": arxiv_id,
        "tags": tags or [],
        "matched_directions": [],
        "related_sources": [source],
        "coverage": [],
    }


def parse_hf_payload(payload: bytes, source_date: date, content_chars: int) -> list[dict[str, Any]]:
    raw = json.loads(payload.decode("utf-8"))
    items: list[dict[str, Any]] = []
    for row in raw if isinstance(raw, list) else raw.get("papers", []):
        wrapper = row if isinstance(row, dict) else {}
        paper = wrapper.get("paper", wrapper)
        if not isinstance(paper, dict):
            continue
        arxiv_id = str(paper.get("id") or paper.get("arxiv_id") or "").strip()
        title = str(paper.get("title") or "").strip()
        if not arxiv_id or not title:
            continue
        authors = []
        for author in paper.get("authors", []) or []:
            if isinstance(author, str):
                authors.append(author)
            elif isinstance(author, dict):
                user = author.get("user") if isinstance(author.get("user"), dict) else {}
                name = author.get("name") or user.get("fullname") or user.get("user")
                if name:
                    authors.append(str(name))
        score = paper.get("upvotes")
        if score is None:
            score = wrapper.get("upvotes", 0)
        summary = str(paper.get("summary") or paper.get("abstract") or "")
        items.append(make_item(
            source="Hugging Face Daily Papers", source_type="paper_feed", kind="paper",
            title=title, summary=clip(summary, content_chars),
            url=f"https://arxiv.org/abs/{arxiv_id}",
            pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
            published_at=datetime.combine(source_date, datetime.min.time(), timezone.utc),
            authors=authors, score=int(score or 0), arxiv_id=arxiv_id,
        ))
    return items


def fetch_hf(start: date, end: date, base_url: str, include_weekends: bool, pause: float, content_chars: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for current in daterange(start, end):
        if not include_weekends and current.weekday() >= 5:
            continue
        url = f"{base_url.rstrip('/')}{HF_API_PATH}?date={current.isoformat()}"
        items.extend(parse_hf_payload(http_get(url), current, content_chars))
        if pause:
            time.sleep(pause)
    return items


def parse_arxiv_payload(payload: bytes, content_chars: int) -> list[dict[str, Any]]:
    root = ET.fromstring(payload)
    items: list[dict[str, Any]] = []
    for entry in root:
        if local_name(entry.tag) != "entry":
            continue
        title = child_text(entry, ("title",))
        summary = child_text(entry, ("summary",))
        published = parse_datetime(child_text(entry, ("published", "updated")))
        entry_id = child_text(entry, ("id",))
        arxiv_id = extract_arxiv_id(entry_id)
        if not title or not arxiv_id:
            continue
        authors = [child_text(child, ("name",)) for child in entry if local_name(child.tag) == "author"]
        authors = [name for name in authors if name]
        tags = [str(child.attrib.get("term")) for child in entry if local_name(child.tag) == "category" and child.attrib.get("term")]
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        for child in entry:
            if local_name(child.tag) != "link":
                continue
            href = str(child.attrib.get("href") or "")
            if child.attrib.get("title") == "pdf" or child.attrib.get("type") == "application/pdf":
                pdf_url = href
            elif child.attrib.get("rel") == "alternate":
                abs_url = href
        items.append(make_item(
            source="arXiv", source_type="primary_paper", kind="paper", title=title,
            summary=clip(summary, content_chars), url=abs_url, pdf_url=pdf_url,
            published_at=published, authors=authors, arxiv_id=arxiv_id, tags=tags,
        ))
    return items


def fetch_arxiv(start: date, end: date, max_results: int, content_chars: int) -> list[dict[str, Any]]:
    category_query = " OR ".join(f"cat:{category}" for category in ARXIV_CATEGORIES)
    date_query = f"submittedDate:[{start:%Y%m%d}0000 TO {end:%Y%m%d}2359]"
    params = urllib.parse.urlencode({
        "search_query": f"({category_query}) AND {date_query}",
        "start": 0, "max_results": max_results, "sortBy": "submittedDate", "sortOrder": "descending",
    })
    return parse_arxiv_payload(http_get(f"{ARXIV_API}?{params}"), content_chars)


def parse_rss_payload(payload: bytes, *, source_name: str, start: date, end: date, content_chars: int) -> list[dict[str, Any]]:
    root = ET.fromstring(payload)
    if local_name(root.tag) == "html":
        raise ValueError("endpoint returned HTML instead of RSS/Atom")
    entries = [element for element in root.iter() if local_name(element.tag) in {"item", "entry"}]
    items: list[dict[str, Any]] = []
    for entry in entries:
        title = child_text(entry, ("title",))
        link = child_text(entry, ("link", "guid", "id"))
        for child in entry:
            if local_name(child.tag) == "link" and child.attrib.get("href"):
                link = str(child.attrib["href"])
                if child.attrib.get("rel") in (None, "", "alternate"):
                    break
        published = parse_datetime(child_text(entry, ("pubdate", "published", "updated", "date")))
        if not title or not in_period(published, start, end):
            continue
        description = child_text(entry, ("description", "summary"))
        full_content = child_text(entry, ("encoded", "content"))
        content = clip(strip_html(full_content or description), content_chars)
        summary = clip(strip_html(description or full_content), min(content_chars, 1200))
        arxiv_id = extract_arxiv_id(link, content, summary, title)
        items.append(make_item(
            source=source_name, source_type="media", kind="article", title=title,
            summary=summary, content=content, url=link, published_at=published,
            arxiv_id=arxiv_id, pdf_url=f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
        ))
    return items


def fetch_rss(url: str, source_name: str, start: date, end: date, content_chars: int) -> list[dict[str, Any]]:
    return parse_rss_payload(http_get(url), source_name=source_name, start=start, end=end, content_chars=content_chars)


def normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return WORD_RE.sub("", value)


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for raw_item in items:
        item = copy.deepcopy(raw_item)
        key = f"arxiv:{item['arxiv_id']}" if item.get("arxiv_id") else f"title:{normalize_title(item.get('title', ''))}"
        if not key.split(":", 1)[1]:
            continue
        if key not in deduped:
            deduped[key] = item
            continue
        existing = deduped[key]
        for source in item.get("related_sources", [item.get("source")]):
            if source and source not in existing["related_sources"]:
                existing["related_sources"].append(source)
        existing["score"] = max(existing.get("score", 0), item.get("score", 0))
        existing["matched_directions"] = sorted(set(existing.get("matched_directions", [])) | set(item.get("matched_directions", [])))
        if item.get("source_type") == "media":
            existing["coverage"].append({"source": item.get("source"), "title": item.get("title"), "url": item.get("url"), "summary": item.get("summary")})
        if item.get("source_type") == "primary_paper" and existing.get("source_type") != "primary_paper":
            preserved_score = existing["score"]
            preserved_sources = existing["related_sources"]
            preserved_coverage = list(existing["coverage"])
            if existing.get("source_type") == "media":
                preserved_coverage.append({"source": existing.get("source"), "title": existing.get("title"), "url": existing.get("url"), "summary": existing.get("summary")})
            existing.update(item)
            existing["score"] = preserved_score
            existing["related_sources"] = preserved_sources
            existing["coverage"] = preserved_coverage
    return list(deduped.values())


def item_sort_key(item: dict[str, Any]) -> tuple[int, str]:
    return int(item.get("score", 0)), str(item.get("published_at", ""))


def parse_named_feed(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("feed must use NAME=URL")
    name, url = value.split("=", 1)
    if not name.strip() or not url.strip():
        raise argparse.ArgumentTypeError("feed must use non-empty NAME=URL")
    return name.strip(), url.strip()


def to_markdown(payload: dict[str, Any]) -> str:
    period = payload["period"]
    lines = [
        f"# PaperStudio Radar · {period['start']} ~ {period['end']}", "",
        f"> 候选 {period['candidate_count']} 条；去重后 {period['item_count']} 条。"
        "这些是关键词宽召回结果，仍需按 directions.md 语义精筛。", "", "## 来源状态", "",
    ]
    for status in payload["source_status"]:
        icon = "✓" if status["status"] == "ok" else "!"
        detail = f" · {status['detail']}" if status.get("detail") else ""
        lines.append(f"- {icon} {status['source']}: {status['status']}{detail}")
    grouped: dict[str, list[dict[str, Any]]] = {key: [] for key in DIRECTIONS}
    for item in payload["items"]:
        primary = (item.get("matched_directions") or [""])[0]
        if primary in grouped:
            grouped[primary].append(item)
    for key, config in DIRECTIONS.items():
        group = grouped[key]
        if not group:
            continue
        lines.extend(["", f"## {config['label']}（{len(group)} 条）", ""])
        for item in group:
            source = " + ".join(item.get("related_sources", []))
            links = [f"[原文]({item['url']})"] if item.get("url") else []
            if item.get("pdf_url"):
                links.append(f"[PDF]({item['pdf_url']})")
            lines.append(f"- **{item['title']}** · {source} · " + " · ".join(links))
            if item.get("summary"):
                lines.append(f"  {clip(item['summary'], 220)}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch multi-source paper/news candidates for PaperStudio Radar")
    period_group = parser.add_mutually_exclusive_group()
    period_group.add_argument("--range", choices=("today", "week", "month"))
    period_group.add_argument("--date", help="YYYY-MM-DD")
    period_group.add_argument("--start", help="YYYY-MM-DD; requires --end")
    parser.add_argument("--end", help="YYYY-MM-DD")
    parser.add_argument("--sources", default="hf,arxiv,qbitai,jiqizhixin", help="comma-separated: hf,arxiv,qbitai,jiqizhixin")
    parser.add_argument("--hf-base-url", default=HF_DEFAULT_BASE)
    parser.add_argument("--include-weekends", action="store_true")
    parser.add_argument("--arxiv-max-results", type=int, default=250)
    parser.add_argument("--content-chars", type=int, default=8000)
    parser.add_argument("--top-k", type=int, default=0)
    parser.add_argument("--all-items", action="store_true", help="skip keyword prefilter")
    parser.add_argument("--jiqizhixin-rss", default=os.environ.get("PAPERSTUDIO_JIQIZHIXIN_RSS", ""), help="机器之心授权 RSS URL；也可用 PAPERSTUDIO_JIQIZHIXIN_RSS")
    parser.add_argument("--feed", action="append", type=parse_named_feed, default=[], metavar="NAME=URL", help="extra RSS/Atom source; repeatable")
    parser.add_argument("--sleep", type=float, default=0.25)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    try:
        start, end = resolve_range(args.range, args.date, args.start, args.end)
    except ValueError as exc:
        parser.error(str(exc))
    if end < start:
        parser.error("--end must be on or after --start")

    requested_sources = {part.strip().lower() for part in args.sources.split(",") if part.strip()}
    matchers = compile_matchers()
    source_status: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

    def collect(source: str, callback: Any) -> None:
        try:
            batch = callback()
            candidates.extend(batch)
            source_status.append({"source": source, "status": "ok", "count": len(batch), "detail": ""})
        except Exception as exc:  # keep other sources alive
            source_status.append({"source": source, "status": "error", "count": 0, "detail": f"{type(exc).__name__}: {exc}"})
            eprint(f"[WARN] {source}: {type(exc).__name__}: {exc}")

    if "hf" in requested_sources:
        collect("Hugging Face Daily Papers", lambda: fetch_hf(start, end, args.hf_base_url, args.include_weekends, args.sleep, args.content_chars))
    if "arxiv" in requested_sources:
        collect("arXiv", lambda: fetch_arxiv(start, end, args.arxiv_max_results, args.content_chars))
    if "qbitai" in requested_sources:
        collect("量子位", lambda: fetch_rss(QBITAI_RSS, "量子位", start, end, args.content_chars))
    if "jiqizhixin" in requested_sources:
        if args.jiqizhixin_rss:
            collect("机器之心", lambda: fetch_rss(args.jiqizhixin_rss, "机器之心", start, end, args.content_chars))
        else:
            source_status.append({"source": "机器之心", "status": "not_configured", "count": 0, "detail": "set PAPERSTUDIO_JIQIZHIXIN_RSS or --jiqizhixin-rss to an authorized RSS/data-service feed"})
    for name, url in args.feed:
        collect(name, lambda name=name, url=url: fetch_rss(url, name, start, end, args.content_chars))

    for item in candidates:
        item["matched_directions"] = tag_directions(item, matchers)
    selected = candidates if args.all_items else [item for item in candidates if item["matched_directions"]]
    items = dedupe_items(selected)
    items.sort(key=item_sort_key, reverse=True)
    if args.top_k > 0:
        items = items[: args.top_k]

    payload = {
        "schema_version": "2.0",
        "period": {"start": start.isoformat(), "end": end.isoformat(), "candidate_count": len(candidates), "item_count": len(items)},
        "directions": {key: config["label"] for key, config in DIRECTIONS.items()},
        "source_status": source_status,
        "items": items,
    }
    rendered = to_markdown(payload) if args.format == "markdown" else json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output_path = os.path.abspath(args.output)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(rendered)
        eprint(f"saved {len(items)} items -> {output_path}")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
