"""Read bounded original units and verified page-image paths from a fixed paper version."""
import argparse
import hashlib
import json
from pathlib import Path


def lookup(inp, manifest, unit_ids=(), pages=(), query=None, max_chars=16000, page_manifest=None, image_root=None):
    if max_chars < 1 or not (unit_ids or pages or query):
        raise ValueError("Select units, PDF file pages or a literal query and a positive budget")
    paper = inp["papers"][0]
    if any(manifest.get(k) != paper[k] for k in ("paper_id", "document_version_id")):
        raise ValueError("Manifest identity mismatch")
    units = {u["unit_id"]: u for u in paper["units"]}
    if not set(unit_ids) <= units.keys():
        raise ValueError("Unknown source unit")
    requested = set(unit_ids)
    requested.update(u["unit_id"] for u in paper["units"] if u.get("locator", {}).get("page") in pages)
    if query:
        requested.update(u["unit_id"] for u in paper["units"] if query.casefold() in u["text"].casefold())
    rows, remaining, used = [], [], 0
    for unit in paper["units"]:
        if unit["unit_id"] not in requested:
            continue
        if used + len(unit["text"]) > max_chars:
            remaining.append(unit["unit_id"])
            continue
        rows.append(unit)
        used += len(unit["text"])
    images = []
    if page_manifest:
        if any(page_manifest.get(k) != paper[k] for k in ("paper_id", "document_version_id")):
            raise ValueError("Page image manifest identity mismatch")
        wanted_pages = set(pages) | {r.get("locator", {}).get("page") for r in rows}
        base = Path(image_root).resolve()
        for page in page_manifest["pages"]:
            if page["page"] not in wanted_pages or not page.get("image"):
                continue
            image = page["image"]
            path = (base / image["path"]).resolve()
            if not path.is_relative_to(base) or hashlib.sha256(path.read_bytes()).hexdigest() != image["sha256"]:
                raise ValueError("Image path/hash mismatch")
            images.append({"page": page["page"], "path": str(path), "sha256": image["sha256"],
                           "review_status": "unreviewed", "action": "Inspect with available vision tool; a path is not a visual finding"})
    appendix = set(manifest.get("appendix_unit_ids", []))
    return {"paper_id": paper["paper_id"], "document_version_id": paper["document_version_id"],
            "units": rows, "images": images, "remaining_unit_ids": remaining,
            "budget_exhausted": bool(remaining), "matched_unit_count": len(requested),
            "appendix_unit_ids": [u["unit_id"] for u in rows if u["unit_id"] in appendix],
            "scope_note": "Lookup does not activate appendix units for a runner; explicitly request their task scope."}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--unit-id", action="append", default=[])
    ap.add_argument("--page", action="append", type=int, default=[])
    ap.add_argument("--query")
    ap.add_argument("--max-chars", type=int, default=16000)
    ap.add_argument("--page-manifest", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    load = lambda p: json.loads(p.read_text(encoding="utf-8"))
    result = lookup(load(args.input), load(args.manifest), args.unit_id, args.page, args.query, args.max_chars,
                    load(args.page_manifest) if args.page_manifest else None,
                    args.page_manifest.parent if args.page_manifest else None)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        if args.output.resolve() in {p.resolve() for p in (args.input, args.manifest, args.page_manifest) if p}:
            raise ValueError("Output cannot overwrite source inputs")
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
