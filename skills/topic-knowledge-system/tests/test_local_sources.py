from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from source_links import source_url, rebase_links
from overview import paper_rows


class LocalSourceTests(unittest.TestCase):
    def test_local_pdf_and_relative_svg_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "papers").mkdir()
            (root / "papers/a.pdf").write_bytes(b"fixture")
            url = "papers/a.pdf#page=2"
            paper_rows([{"name": "A", "method": "Cache", "url": url}], 5)
            html = '<a href="papers/a.pdf#page=2">A</a>'
            self.assertIn('../papers/a.pdf#page=2', rebase_links(html, [url], root, root / "diagrams"))
            self.assertEqual(rebase_links(html, [url], root, root), html)

    def test_unsafe_urls_and_missing_sources_fail(self):
        for url in ("javascript:alert(1)", "file:///etc/passwd", "../a.pdf", "%2e%2e/a.pdf", "/a.pdf", "//evil/a.pdf", "a.svg", "a.pdf?x=1"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                source_url(url)
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            rebase_links('<a href="missing.pdf">x</a>', ["missing.pdf"], Path(tmp), Path(tmp))


if __name__ == "__main__":
    unittest.main()
