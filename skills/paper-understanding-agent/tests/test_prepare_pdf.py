"""Exercise the PDF handoff with local PDFs and no model or network."""

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

try:
    import pymupdf
except ImportError:
    pymupdf = None

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_pdf.py"


@unittest.skipUnless(pymupdf, "optional PyMuPDF dependency is unavailable")
class PreparePdfTests(unittest.TestCase):
    def test_selected_pages_preserve_pdf_identity_and_report_missing_text(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "paper.pdf"
            with pymupdf.open() as pdf:
                pdf.new_page().insert_text((40, 40), "Abstract: A test paper.")
                pdf.new_page().insert_text((40, 40), "This page is outside the sample.")
                pdf.new_page().set_rotation(90)
                pdf.save(source)
            out = root / "result"
            subprocess.run([sys.executable, str(SCRIPT), str(source), "--paper-id", "test",
                            "--version", "v1", "--pages", "1,3", "--render-pages", "3",
                            "--out", str(out)], check=True)
            paper = json.loads((out / "input.json").read_text(encoding="utf-8"))["papers"][0]
            manifest = json.loads((out / "page-manifest.json").read_text(encoding="utf-8"))
            digest = sha256(source.read_bytes()).hexdigest()
            self.assertEqual(paper["document_version_id"], f"v1@sha256:{digest}")
            self.assertEqual(manifest["pdf_sha256"], digest)
            self.assertEqual(paper["coverage"], "partial")
            self.assertEqual([row["page"] for row in manifest["pages"]], [1, 3])
            self.assertEqual([unit["locator"]["page"] for unit in paper["units"]], [1])
            self.assertIn("Abstract: A test paper.", paper["units"][0]["text"])
            self.assertEqual(manifest["pages"][0]["unit_ids"], [paper["units"][0]["unit_id"]])
            blank = manifest["pages"][1]
            self.assertTrue(blank["needs_text_review"])
            self.assertEqual(blank["rotation"], 90)
            image = (out / blank["image"]["path"]).read_bytes()
            self.assertTrue(image.startswith(b"\x89PNG"))
            self.assertEqual(blank["image"]["sha256"], sha256(image).hexdigest())


if __name__ == "__main__":
    unittest.main()
