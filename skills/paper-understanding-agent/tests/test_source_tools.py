import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_pdf import prepare_pdf
from prepare_scope import draft
from import_visual import merge
from read_evidence import lookup
import run_agent

try:
    import pymupdf
except ImportError:
    pymupdf = None


@unittest.skipUnless(pymupdf, "optional PyMuPDF unavailable")
class SourceToolsTests(unittest.TestCase):
    def test_pdf_scope_image_lookup_and_reviewed_transcription(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "paper.pdf"
            with pymupdf.open() as document:
                page = document.new_page()
                page.insert_text((40, 50), "Table 1. Latency is 12 ms.")
                document.save(pdf)
            out = root / "parsed"
            prepare_pdf(argparse.Namespace(pdf=pdf, paper_id="p", version="v1", source_url=None, pages=None,
                                          render_pages="1", dpi=144, out=out))
            load = lambda name: json.loads((out / name).read_text())
            inp, pages = load("input.json"), load("page-manifest.json")
            plan = draft(inp, pages)
            schema = json.loads((ROOT / "runtime/references/workflow-output.schema.json").read_text())
            validator = run_agent.workflow.validator_class(ROOT / "runtime")
            with self.assertRaisesRegex(run_agent.workflow.WorkflowError, "draft"):
                run_agent.workflow.validate_plan(inp, plan, schema, validator)
            plan["review_status"] = "reviewed"
            found = lookup(inp, plan, pages=[1], page_manifest=pages, image_root=out)
            self.assertEqual(found["images"][0]["review_status"], "unreviewed")
            review = {k: inp["papers"][0][k] for k in ("paper_id", "document_version_id")}
            review.update(status="reviewed", method="vlm", reviewer="synthetic fixture", transcriptions=[{
                "page": 1, "label": "Table 1", "image_sha256": pages["pages"][0]["image"]["sha256"],
                "bbox_px": [40, 40, 400, 150], "text": "Latency 12 ms", "region": "body", "section_id": "unsectioned-main"}])
            updated, expanded = merge(inp, plan, pages, review, out)
            run_agent.workflow.validate_plan(updated, expanded, schema, validator)
            self.assertEqual(updated["papers"][0]["units"][-1]["origin"], "visual_transcription")
            bad = copy.deepcopy(review)
            bad["status"] = "unreviewed"
            with self.assertRaises(ValueError):
                merge(inp, plan, pages, bad, out)
            bad = copy.deepcopy(review)
            bad["transcriptions"][0]["bbox_px"] = [0, 0, 99999, 99999]
            with self.assertRaisesRegex(ValueError, "outside"):
                merge(inp, plan, pages, bad, out)
            image = out / pages["pages"][0]["image"]["path"]
            image.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                lookup(inp, plan, pages=[1], page_manifest=pages, image_root=out)


if __name__ == "__main__":
    unittest.main()
