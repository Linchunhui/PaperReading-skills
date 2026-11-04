"""Import explicitly reviewed image transcriptions as provenance-marked source units."""
import argparse
from copy import deepcopy
import hashlib
import json
import struct
from pathlib import Path


def merge(inp, manifest, page_manifest, review, image_root):
    result, plan = deepcopy(inp), deepcopy(manifest)
    paper, scope = result["papers"][0], plan["scope"]
    for document in (manifest, page_manifest, review):
        if any(document.get(k) != paper[k] for k in ("paper_id", "document_version_id")):
            raise ValueError("Visual evidence paper/version mismatch")
    if review.get("status") != "reviewed" or review.get("method") not in {"vlm", "manual"} or not review.get("reviewer"):
        raise ValueError("Only explicitly reviewed transcriptions may enter paper text")
    records = review.get("transcriptions", [])
    if not records:
        raise ValueError("No transcription supplied; visual interpretations remain separate observations")
    existing = {u["unit_id"] for u in paper["units"]}
    for row in records:
        page = next((p for p in page_manifest["pages"] if p["page"] == row["page"]), None)
        if not page or not page.get("image") or row.get("image_sha256") != page["image"]["sha256"]:
            raise ValueError("Transcription must identify a rendered image and its hash")
        root = Path(image_root).resolve()
        image = (root / page["image"]["path"]).resolve()
        if not image.is_relative_to(root) or hashlib.sha256(image.read_bytes()).hexdigest() != row["image_sha256"]:
            raise ValueError("Visual source image changed")
        if not isinstance(row.get("text"), str) or not row["text"].strip() or not row.get("label"):
            raise ValueError("Transcription requires literal text and figure/table/formula label")
        bbox = row.get("bbox_px")
        if not isinstance(bbox, list) or len(bbox) != 4 or not all(isinstance(v, (float, int)) and v >= 0 for v in bbox) or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            raise ValueError("bbox_px must be x0,y0,x1,y1 in the reviewed page image")
        raw_image = image.read_bytes()
        if raw_image[:8] != b"\x89PNG\r\n\x1a\n" or len(raw_image) < 24:
            raise ValueError("Expected a rendered PNG page")
        width, height = struct.unpack(">II", raw_image[16:24])
        if bbox[2] > width or bbox[3] > height:
            raise ValueError("Visual bounding box is outside the image")
        uid = "visual-" + hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]
        if uid in existing:
            raise ValueError("Duplicate visual transcription")
        existing.add(uid)
        provenance = {"reviewed": True, "reviewer": review["reviewer"], "method": review["method"],
                      "image_sha256": row["image_sha256"], "pdf_sha256": page_manifest["pdf_sha256"],
                      "label": row["label"], "bbox_px": bbox, "dpi": page["image"]["dpi"]}
        paper["units"].append({"unit_id": uid, "text": row["text"], "origin": "visual_transcription", "source_type": "paper",
                              "locator": {"page": row["page"], "figure_or_table": row["label"]}, "visual_provenance": provenance})
        if row.get("region") == "appendix":
            plan.setdefault("appendix_unit_ids", []).append(uid)
            scope["excluded_units"].append({"unit_id": uid, "reason": "Reviewed appendix transcription; activate explicitly when needed"})
        elif row.get("region") == "body":
            section = next((s for s in scope["sections"] if s["section_id"] == row.get("section_id")), None)
            if not section:
                raise ValueError("Body transcription requires an existing reviewed section_id")
            section["unit_ids"].append(uid)
            scope["main_unit_ids"].append(uid)
            scope["pages"].append({"page_id": uid, "unit_ids": [uid]})
        else:
            raise ValueError("Visual source region must be body or appendix")
    plan.setdefault("visual_reviews", []).append({k: review[k] for k in ("paper_id", "document_version_id", "status", "method", "reviewer")})
    return result, plan


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("input", "manifest", "page-manifest", "review", "out"):
        ap.add_argument("--" + name, required=True, type=Path)
    args = ap.parse_args()
    load = lambda p: json.loads(p.read_text(encoding="utf-8"))
    inp, manifest = merge(load(args.input), load(args.manifest), load(args.page_manifest), load(args.review), args.page_manifest.parent)
    args.out.mkdir(parents=True, exist_ok=False)
    for name, content in (("input.json", inp), ("manifest.json", manifest)):
        (args.out / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
