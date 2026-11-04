"""Local contract checks for crop and relay helpers; no live research."""
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import gptr_web_relay


def synthetic_pdf():
    stream = b"q 1 0 0 rg 20 20 100 80 re f Q\n"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(data)


@unittest.skipUnless(shutil.which("pdfinfo") and shutil.which("pdftoppm"), "Optional Poppler crop tools unavailable")
class CropTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.pdf = self.folder / "synthetic.pdf"
        self.pdf.write_bytes(synthetic_pdf())
        self.output = self.folder / "crop.png"
        self.manifest = self.folder / "crop.json"

    def tearDown(self):
        self.temp.cleanup()

    def run_crop(self, box=("20", "20", "80", "60"), page="1"):
        return subprocess.run([
            sys.executable, "-B", str(ROOT / "scripts" / "crop_original_figure.py"),
            "--pdf", str(self.pdf), "--page", page, "--figure", "1",
            "--box-px", *box, "--dpi", "72", "--output", str(self.output),
            "--manifest", str(self.manifest), "--version", "synthetic-v1",
        ], capture_output=True, text=True)

    def test_real_poppler_crop_and_provenance(self):
        result = self.run_crop()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.output.read_bytes()
        self.assertEqual(struct.unpack(">II", data[16:24]), (80, 60))
        info = json.loads(self.manifest.read_text())
        self.assertEqual(info["source_sha256"], hashlib.sha256(self.pdf.read_bytes()).hexdigest())
        self.assertEqual(info["png_sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(info["source_version"], "synthetic-v1")
        self.assertEqual(info["page_count"], 1)
        self.assertIn("required", info["visual_review"])

    def test_existing_output_is_not_overwritten(self):
        self.output.write_bytes(b"existing")
        result = self.run_crop()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_bytes(), b"existing")
        self.assertFalse(self.manifest.exists())

    def test_invalid_page_and_bounds_are_rejected(self):
        for box, page in [(("20", "20", "80", "60"), "2"), (("195", "195", "50", "50"), "1")]:
            with self.subTest(page=page, box=box):
                result = self.run_crop(box, page)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.exists())


class RelayContractTests(unittest.TestCase):
    def test_help_and_invalid_budget(self):
        command = [sys.executable, "-B", str(ROOT / "scripts" / "gptr_web_relay.py")]
        self.assertEqual(subprocess.run(command + ["--help"], capture_output=True).returncode, 0)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "run"
            result = subprocess.run(command + ["--question", "Synthetic test", "--out-dir", str(out), "--max-queries", "0"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(out.exists())

    def test_json_write_is_complete_and_temp_file_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "response.json"
            value = {"provider": "synthetic-test", "results": []}
            gptr_web_relay.write_json(path, value)
            self.assertEqual(json.loads(path.read_text()), value)
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_incompatible_package_version_stops_before_run(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(gptr_web_relay.importlib.metadata, 'version', return_value='0.15.0'):
            with self.assertRaisesRegex(RuntimeError, 'detected 0.15.0'):
                asyncio.run(gptr_web_relay.main(argparse.Namespace(out_dir=Path(folder)/'run', mode='live', question='test')))
            self.assertEqual(json.loads((Path(folder)/'run/gptr-run.json').read_text())['status'], 'blocked')

    def test_missing_dependency_has_explicit_error(self):
        try:
            importlib.metadata.version("gpt-researcher")
        except importlib.metadata.PackageNotFoundError:
            pass
        else:
            self.skipTest("Dependency is installed; absence guard is not applicable")
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "run"
            result = subprocess.run([
                sys.executable, "-B", str(ROOT / "scripts" / "gptr_web_relay.py"),
                "--question", "Synthetic test", "--out-dir", str(out),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("not installed", result.stderr)
            self.assertEqual(json.loads((out/'gptr-run.json').read_text())['status'], 'blocked')


if __name__ == "__main__":
    unittest.main()
