"""Focused structural regressions; semantic truth and pixels need independent review."""
import tempfile
import unittest
from pathlib import Path
from validate_html import validate_html

PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jp1sAAAAASUVORK5CYII='
FIG = f'<figure data-figure-role="original-core"><img src="{PNG}" alt="Original Figure 1"><figcaption>Figure 1: follow the input and output. <a href="https://example.org/paper#fig1">Source</a></figcaption></figure>'
EX = '<p class="core-figure-exception" data-source="provided papers.md §3">Only the method text was supplied; no figure asset or PDF was provided.</p>'
def body(content, state='embedded', ident='a'):
    return f'<article id="{ident}" data-status="formal" data-paper-body="true" data-core-figure-status="{state}">{content}</article>'

class CoverageTests(unittest.TestCase):
    def check(self, html, strict=True):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.html';p.write_text(html)
            return validate_html(p,require_core_figures=strict)
    def test_original(self): self.assertTrue(self.check(body(FIG))['ok'])
    def test_source_material(self): self.assertTrue(self.check(body(FIG.replace('<figure ', '<figure data-source="provided original Figure 1" ').replace('<a href="https://example.org/paper#fig1">Source</a>','')))['ok'])
    def test_no_bodies(self): self.assertFalse(self.check('<p>Text only</p>')['ok'])
    def test_legacy_compatibility(self): self.assertTrue(self.check('<p>Text only</p>',False)['ok'])
    def test_teaching_svg_not_original(self): self.assertFalse(self.check(body('<svg><text>Input → output</text></svg>'))['ok'])
    def test_navigation_not_coverage(self): self.assertFalse(self.check(FIG+body('Text'))['ok'])
    def test_some_not_all(self): self.assertFalse(self.check(body(FIG)+body('Missing',ident='b'))['ok'])
    def test_unmarked_formal(self): self.assertFalse(self.check(body(FIG)+'<article data-status="formal" id="b">Missing</article>')['ok'])
    def test_missing_status(self): self.assertFalse(self.check(body(FIG).replace('data-core-figure-status="embedded"',''))['ok'])
    def test_valid_exception(self): self.assertTrue(self.check(body(EX,'unavailable'))['ok'])
    def test_not_applicable(self): self.assertTrue(self.check(body(EX.replace('Only the method text was supplied; no figure asset or PDF was provided.','The supplied complete theoretical note contains a proof and no figures.'),'not-applicable'))['ok'])
    def test_missing_exception_source(self): self.assertFalse(self.check(body(EX.replace('data-source="provided papers.md §3"',''),'unavailable'))['ok'])
    def test_hidden_exception(self): self.assertFalse(self.check(body(EX.replace('<p ','<p hidden '),'unavailable'))['ok'])
    def test_no_caption(self): self.assertFalse(self.check(body(FIG.replace('figcaption','div')))['ok'])
    def test_bad_data(self): self.assertFalse(self.check(body(FIG.replace(PNG,'data:image/png;base64,%%%')))['ok'])
    def test_external_image(self): self.assertFalse(self.check(body(FIG.replace(PNG,'https://example.org/fig.png')))['ok'])
    def test_duplicate_id(self): self.assertFalse(self.check(body(FIG)+body(FIG))['ok'])
    def test_large_report_not_capped(self):
        result=self.check(''.join(body(FIG,ident=str(i)) for i in range(57)))
        self.assertTrue(result['ok']); self.assertEqual(result['figure_coverage']['embedded'],57)

if __name__=='__main__': unittest.main()
