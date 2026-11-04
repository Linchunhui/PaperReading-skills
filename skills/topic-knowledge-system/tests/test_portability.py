"""Offline end-to-end checks using only bundled public examples."""
import json
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.sources = []
        self.fragments = []
        self.stylesheets = []

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if "id" in fields:
            self.ids.append(fields["id"])
        if tag in {"img", "script", "iframe", "source"} and fields.get("src"):
            self.sources.append(fields["src"])
        if fields.get("href", "").startswith("#"):
            self.fragments.append(fields["href"][1:])
        if tag == "link" and fields.get("rel") == "stylesheet":
            self.stylesheets.append(fields.get("href"))


class TopicPortabilityTests(unittest.TestCase):
    def test_public_example_generates_offline_html_and_svg(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "report.html"
            diagrams = Path(folder) / "diagrams"
            subprocess.run(
                [sys.executable, "-B", str(ROOT / "scripts" / "build_topic.py"),
                 str(ROOT / "references" / "grpo-example.json"), str(out), "--svg-dir", str(diagrams)],
                capture_output=True, text=True, check=True,
            )
            content = out.read_text(encoding="utf-8")
            self.assertIn("<style>", content)
            self.assertIn("data:image/svg+xml;base64,", content)
            assets = Assets()
            assets.feed(content)
            self.assertEqual(len(assets.ids), len(set(assets.ids)))
            self.assertTrue(set(assets.fragments) <= set(assets.ids))
            self.assertFalse(assets.stylesheets)
            self.assertTrue(all(source.startswith("data:") for source in assets.sources))
            files = sorted(diagrams.glob("*.svg"))
            self.assertEqual(len(files), 5)
            for path in files:
                self.assertTrue(ET.parse(path).getroot().get("viewBox"))

    def test_input_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            original = (ROOT / "references" / "grpo-example.json").read_bytes()
            path.write_bytes(original)
            result = subprocess.run(
                [sys.executable, "-B", str(ROOT / "scripts" / "build_topic.py"), str(path), str(path)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
