"""Offline checks for original_figures; all PNG bytes are synthetic test data."""
import base64
import copy
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_topic


def png_bytes(width=320, height=160):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    rows = (b"\x00" + b"\xff\xff\xff" * width) * height
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows))
            + chunk(b"IEND", b""))


class OriginalFigureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.input_dir = (self.root / "input").resolve()
        self.input_dir.mkdir()
        self.png = png_bytes()
        (self.input_dir / "figure.png").write_bytes(self.png)
        self.topic = json.loads((ROOT / "references" / "grpo-example.json").read_text())
        self.figure = {
            "file": "figure.png", "figure": "S1", "page": 3, "pdf": "paper.pdf",
            "alt": "Synthetic white test image", "caption": "Synthetic fixture only.",
        }

    def tearDown(self):
        self.temp.cleanup()

    def render(self, figure=None):
        topic = copy.deepcopy(self.topic)
        topic["branches"][0]["papers"][0]["original_figures"] = [figure or self.figure]
        return build_topic.build(topic, self.input_dir)[0]

    def test_original_png_bytes_are_embedded_without_conversion(self):
        html = self.render()
        encoded = re.search(r'data:image/png;base64,([^"]+)', html).group(1)
        self.assertEqual(base64.b64decode(encoded), self.png)
        self.assertIn('width="320" height="160"', html)
        self.assertIn("paper.pdf#page=3", html)
        self.assertIn("原文图 S1", html)
        self.assertLess(html.index('class="original-figure"'), html.index('class="experiment"'))

    def test_reading_width_and_text_escaping(self):
        item = {**self.figure, "reading_width": 700, "alt": '<img onerror="x">',
                "caption": "<script>unexpected()</script>"}
        html = self.render(item)
        self.assertIn("--reading-width:700px", html)
        self.assertIn("&lt;script&gt;unexpected()&lt;/script&gt;", html)
        self.assertNotIn("<script>unexpected()", html)
        self.assertIn('alt="&lt;img onerror=&quot;x&quot;&gt;"', html)

    def test_pdf_links_and_page_fragments(self):
        self.assertEqual(build_topic.original_figure_pdf("paper.pdf", 3), "paper.pdf#page=3")
        self.assertEqual(build_topic.original_figure_pdf("https://example.org/paper.pdf#page=3", 3),
                         "https://example.org/paper.pdf#page=3")
        for url in ("paper.pdf#page=2", "/private/paper.pdf", "javascript:alert(1)", "paper.txt", "paper.pdf?x=1"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                build_topic.original_figure_pdf(url, 3)

    def test_png_path_traversal_and_symlink_escape_are_rejected(self):
        outside = self.root / "outside.png"
        outside.write_bytes(self.png)
        (self.input_dir / "escape.png").symlink_to(outside)
        for value in ("../outside.png", str(outside), "escape.png"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.render({**self.figure, "file": value})

    def test_invalid_header_extension_and_missing_file_are_rejected(self):
        (self.input_dir / "invalid.png").write_bytes(b"not PNG data")
        (self.input_dir / "wrong.jpg").write_bytes(self.png)
        for name in ("invalid.png", "wrong.jpg"):
            with self.subTest(file=name), self.assertRaises(ValueError):
                self.render({**self.figure, "file": name})
        with self.assertRaises(FileNotFoundError):
            self.render({**self.figure, "file": "absent.png"})

    def test_invalid_metadata_is_rejected(self):
        for changes in ({"page": 0}, {"page": True}, {"page": "3"}, {"figure": 0},
                        {"figure": " "}, {"reading_width": 0}, {"reading_width": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.render({**self.figure, **changes})

    @unittest.skipUnless(shutil.which("node"), "Node.js is optional for the JavaScript state test")
    def test_zoom_button_state_transitions(self):
        script = re.search(r"<script>(.*?)</script>", self.render(), re.S).group(1)
        harness = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
function element() {
  const classes = new Set();
  return {
    attrs: {}, handlers: {}, textContent: '', tabIndex: undefined, scroll: null,
    classList: {toggle(name) { if(classes.has(name)){classes.delete(name);return false;} classes.add(name);return true; }},
    addEventListener(name, fn) { this.handlers[name] = fn; },
    setAttribute(name, value) { this.attrs[name] = String(value); },
    getAttribute(name) { return this.attrs[name]; },
    removeAttribute(name) { delete this.attrs[name]; if(name==='tabindex')this.tabIndex=undefined; },
    scrollTo(x,y) { this.scroll=[x,y]; }
  };
}
const zoom=element(), frame=element(), button=element(), art=element();
button.attrs['aria-controls']='art';
const document={
  getElementById(id) { return {'map-zoom':zoom,'map-frame':frame,art}[id]; },
  querySelectorAll(selector) { assert.equal(selector,'.figure-zoom');return [button]; }
};
vm.runInNewContext(SCRIPT, {document});
button.handlers.click();
assert.equal(button.attrs['aria-pressed'],'true');
assert.equal(button.textContent,'缩回版宽');
assert.equal(art.tabIndex,0);
button.handlers.click();
assert.equal(button.attrs['aria-pressed'],'false');
assert.equal(button.textContent,'放大原图');
assert.equal(art.tabIndex,undefined);
assert.deepEqual(art.scroll,[0,0]);
"""
        result = subprocess.run([shutil.which("node"), "-e", "const SCRIPT=" + json.dumps(script) + ";\n" + harness],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
