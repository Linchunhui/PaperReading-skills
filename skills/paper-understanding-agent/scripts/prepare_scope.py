"""Create a reviewable scope draft; never guess that a PDF outline is verified scope."""
import argparse
from collections import OrderedDict
import json
from pathlib import Path


def draft(inp, page_manifest=None):
    paper = inp["papers"][0]
    main, external = [], []
    pages = OrderedDict()
    for unit in paper["units"]:
        if unit.get("source_type", "paper") != "paper":
            external.append(unit["unit_id"])
            continue
        main.append(unit["unit_id"])
        page = str(unit.get("locator", {}).get("page", "unpaged"))
        pages.setdefault(page, []).append(unit["unit_id"])
    return {"paper_id": paper["paper_id"], "document_version_id": paper["document_version_id"],
            "review_status": "draft", "appendix_unit_ids": [], "appendix_sections": [],
            "scope_hints": {"outline": (page_manifest or {}).get("outline_hints", []),
                            "page_labels": [{"page": p["page"], "label_hints": p.get("label_hints", [])}
                                            for p in (page_manifest or {}).get("pages", [])]},
            "scope": {"main_unit_ids": main, "metadata_unit_ids": [], "reference_unit_ids": [],
                "external_unit_ids": external, "excluded_units": [], "unresolved_units": [],
                "pages": [{"page_id": "pdf-" + page, "unit_ids": ids} for page, ids in pages.items()],
                "sections": [{"section_id": "unsectioned-main", "title": "Unreviewed section boundaries", "unit_ids": list(main)}] if main else [],
                "original_abstract_spans": [],
                "boundary_notes": ["Draft only: review reading order, body/reference/appendix boundaries, chapter groups and abstract spans before execution."]}}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--page-manifest", type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    load = lambda p: json.loads(p.read_text(encoding="utf-8"))
    if args.output.exists():
        raise ValueError("Use a new output path; do not overwrite a reviewed scope")
    inp = load(args.input)
    pages = load(args.page_manifest) if args.page_manifest else None
    if pages and any(pages[k] != inp["papers"][0][k] for k in ("paper_id", "document_version_id")):
        raise ValueError("Page manifest belongs to a different paper version")
    args.output.write_text(json.dumps(draft(inp, pages), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
