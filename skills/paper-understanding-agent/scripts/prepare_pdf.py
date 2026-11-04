"""Extract page evidence and render selected pages from a local PDF with PyMuPDF."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re


def select_pages(spec, page_count):
    if spec is None:
        return list(range(1, page_count + 1))
    pages = set()
    for item in spec.split(","):
        match = re.fullmatch(r"(\d+)(?:-(\d+))?", item.strip())
        if not match:
            raise ValueError(f"Invalid page or page range: {item!r}")
        start = int(match[1])
        end = int(match[2] or match[1])
        if not 1 <= start <= end <= page_count:
            raise ValueError(f"Page range {item!r} is outside 1–{page_count} or reversed")
        pages.update(range(start, end + 1))
    return sorted(pages)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_pdf(args):
    import pymupdf

    pdf = args.pdf.read_bytes()
    digest = sha256(pdf).hexdigest()
    version = f"{args.version}@sha256:{digest}"
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        if not document.is_pdf or document.needs_pass or not document.page_count:
            raise ValueError("Expected a readable, nonempty PDF")
        selected = select_pages(args.pages, document.page_count)
        render = set(select_pages(args.render_pages, document.page_count)) if args.render_pages else set()
        if render.difference(selected):
            raise ValueError("--render-pages must be within the selected --pages")

        args.out.mkdir(parents=True, exist_ok=False)
        if render:
            (args.out / "pages").mkdir()
        units = []
        pages = []
        for number in selected:
            page = document[number - 1]
            page_units = []
            flags = pymupdf.TEXTFLAGS_BLOCKS & ~pymupdf.TEXT_PRESERVE_IMAGES
            for x0, y0, x1, y1, text, block_number, block_type in page.get_text("blocks", flags=flags):
                if block_type != 0 or not text.strip():
                    continue
                unit_id = f"p{number}-b{block_number}"
                units.append({
                    "unit_id": unit_id,
                    "text": text,
                    "origin": "parsed_text",
                    "source_type": "paper",
                    "locator": {"page": number, "bbox": [x0, y0, x1, y1]},
                })
                page_units.append(unit_id)
            page_text = "".join(u["text"] for u in units if u["unit_id"] in page_units)
            flags_review = []
            if not page_units:
                flags_review.append("empty_or_image_only")
            if "\ufffd" in page_text:
                flags_review.append("replacement_characters")
            if page_units and len(page_text.strip()) < 40:
                flags_review.append("sparse_text")
            labels = [{"unit_id": u["unit_id"], "text": u["text"][:200]}
                      for u in units if u["unit_id"] in page_units and
                      re.match(r"(?i)^\s*(appendix|appendices|supplement|figure|fig\.|table|附录|图\s*\d|表\s*\d)", u["text"])]
            record = {"page": number, "label": page.get_label(), "rotation": page.rotation,
                      "unit_ids": page_units, "needs_text_review": bool(flags_review),
                      "text_review_flags": flags_review, "label_hints": labels,
                      "reading_order_status": "unreviewed"}
            if number in render:
                image_path = f"pages/p{number}.png"
                image = page.get_pixmap(dpi=args.dpi, alpha=False, annots=False).tobytes("png")
                (args.out / image_path).write_bytes(image)
                record["image"] = {"path": image_path, "sha256": sha256(image).hexdigest(), "dpi": args.dpi}
            pages.append(record)
        source = {"paper_id": args.paper_id, "document_version_id": version,
                  "version_label": args.version, "source_url": args.source_url,
                  "pdf_filename": args.pdf.name, "pdf_sha256": digest, "page_count": document.page_count,
                  "pymupdf_version": pymupdf.__version__, "pages": pages,
                  "outline_hints": [{"level": level, "title": title, "page": page} for level, title, page in document.get_toc()],
                  "hints_status": "unreviewed; not semantic scope assignments"}

    write_json(args.out / "input.json", {
        "schema_version": "1.0",
        "papers": [{"paper_id": args.paper_id, "document_version_id": version, "coverage": "partial",
                    "units": units, "assets": []}],
        "options": {"profile": "comprehensive"},
    })
    write_json(args.out / "page-manifest.json", source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--paper-id", required=True)
    parser.add_argument("--version", required=True, help="Verified source version label")
    parser.add_argument("--source-url", help="Optional original source URL, recorded without fetching it")
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    parser.add_argument("--pages", help="Comma-separated PDF file pages or ranges, counted from 1. Default: all")
    parser.add_argument("--render-pages", help="Selected file pages to render, e.g. 1,4-5. Default: none")
    parser.add_argument("--dpi", type=int, default=144)
    args = parser.parse_args()
    if not args.paper_id.strip() or not args.version.strip():
        parser.error("--paper-id and --version must be nonempty")
    if not 36 <= args.dpi <= 300:
        parser.error("--dpi must be between 36 and 300")
    try:
        prepare_pdf(args)
    except ImportError:
        parser.exit(1, "PDF preparation requires PyMuPDF. Install scripts/requirements-pdf.txt.\n")
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(1, f"PDF preparation failed: {exc}\n")


if __name__ == "__main__":
    main()
