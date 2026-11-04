from html import escape
from pathlib import Path
import re
from string import Template
from xml.etree import ElementTree as ET

import overview as drawing

TEMPLATE = (Path(__file__).resolve().parents[1] / 'assets/tree.svg').read_text(encoding='utf-8')
SVG_NS = 'http://www.w3.org/2000/svg'
NS = '{' + SVG_NS + '}'
ET.register_namespace('', SVG_NS)


def scoped_template_css(scope='.method-tree .tree-map'):
    original = re.search(r'<style>(.*?)</style>', TEMPLATE, re.S).group(1)
    rules = []
    for selector, body in re.findall(r'([^{}]+)\{([^{}]*)\}', original):
        selectors = [scope if part.strip() in (':root', 'svg') else f'{scope} {part.strip()}'
                     for part in selector.split(',')]
        if selector.strip() == 'svg':
            body = body.replace('aspect-ratio:1920/1080;', '')
        rules.append(f'{",".join(selectors)}{{{body}}}')
    return '\n'.join(rules)


def format_svg(svg, cid, variant, paper_ids, standalone):
    title, desc = (svg.find(NS + tag) for tag in ('title', 'desc'))
    prefix = f'tree-{cid}-{variant}'
    title.set('id', prefix + '-title')
    desc.set('id', prefix + '-desc')
    svg.set('aria-labelledby', f'{prefix}-title {prefix}-desc')
    svg.set('class', f'tree-map tree-{variant}')
    if variant == 'narrow':
        svg.set('preserveAspectRatio', 'xMinYMin meet')
    svg.set('role', 'group')
    style = svg.find(NS + 'style')
    if standalone:
        style.text = scoped_template_css('.tree-map') + TREE_TEXT_CSS
    else:
        svg.remove(style)

    papers = [a for a in svg.findall(NS + 'a') if a.get('class') == 'paper']
    assert len(papers) == len(paper_ids)
    for anchor, pid in zip(papers, paper_ids):
        original = anchor.get('href')
        if not standalone:
            anchor.set('href', f'#paper-{pid}')
            anchor.attrib.pop('target', None)
            anchor.attrib.pop('rel', None)
        texts = anchor.findall(NS + 'text')
        name = ' '.join(t.text for t in texts if t.get('class') == 'paper-title')
        date = next(t for t in texts if t.get('class') == 'date')
        anchor.set('aria-label', f'打开 {name} 原文' if standalone else f'跳到 {name} 的正文')
        if variant == 'wide':
            source_x, source_y = float(date.get('x')) + 94, date.get('y')
            end = False
        else:
            source_x, source_y = 263, texts[0].get('y')
            end = True
        source = ET.SubElement(svg, NS + 'a', {'href': original, 'target': '_blank',
                               'rel': 'noopener noreferrer', 'class': 'tree-original',
                               'aria-label': f'打开 {name} 原文'})
        attrs = {'x': f'{source_x:g}', 'y': source_y, 'class': 'date'}
        if end:
            attrs['text-anchor'] = 'end'
        ET.SubElement(source, NS + 'text', attrs).text = '原文 ↗'

    return ET.tostring(svg, encoding='unicode')


def wide_body(core, papers, number, entry_label):
    width, left, right = 1280, 24, 1256
    root_width, trunk_x, paper_x, method_x = 166, 213, 252, 555
    palette = f'branch-{number}'
    top, y = 34, 53
    wires = [drawing.path(f'M{left} {top}H{right}')]
    cards, centers = [], []
    for j, paper in enumerate(papers):
        title = drawing.wrap(paper['name'], method_x - paper_x - 24, 17.5)
        name_y, date_y = y + 20, y + 43 + 25 * (len(title) - 1)
        copy = drawing.wrap(paper['method'], right - method_x - 10, 14.8)
        center = y + 15
        centers.append(center)
        bottom = max(date_y + 19, name_y + 22 * (len(copy) - 1) + 20)
        wires.extend([drawing.path(f'M{trunk_x} {center}H{paper_x-12}', f'leaf-wire {palette}'),
                      drawing.dot(paper_x - 12, center, palette)])
        if j < len(papers) - 1:
            wires.append(drawing.path(f'M{paper_x} {bottom-7}H{right}'))
        hitbox = f'<path class="tree-hitbox" d="M{paper_x-9} {y-7}H{right+8}V{bottom-7}H{paper_x-9}Z" fill="transparent" aria-hidden="true"/>'
        card = hitbox + drawing.block(paper_x, name_y, title, 25, 'paper-title')
        card += drawing.txt(paper_x, date_y, paper.get('date') or '日期待核', 'date')
        card += drawing.block(method_x, name_y + 1, copy, 22, 'paper-copy')
        cards.append(drawing.paper_link(paper, card, 'paper'))
        y = bottom
    middle = (centers[0] + centers[-1]) / 2
    wires.append(drawing.path(f'M{left + root_width} {middle}H{trunk_x} M{trunk_x} {centers[0]}V{centers[-1]}', 'trunk'))
    labels = [drawing.txt(left, 23, '核心方法', 'col-label'),
              drawing.txt(paper_x, 23, entry_label, 'col-label'),
              drawing.txt(method_x, 23, '解决思路', 'col-label')]
    labels.append(drawing.rect(left, middle - 34, root_width, 68, 'root-fill', 8))
    labels.append(drawing.txt(left + 12, middle + 1, core['name'], 'root-title'))
    labels.append(drawing.txt(left + 12, middle + 21, core['label'], 'root-desc'))
    height = y + 5
    return drawing.rect(0, 0, width, height, 'bg') + ''.join(wires + labels + cards), width, height


def narrow_body(core, papers, number):
    width = 372
    palette = f'branch-{number}'
    root_bottom = 73
    y = root_bottom + 8
    wires, cards = [], []
    cards.append(drawing.rect(10, 10, 208, root_bottom - 10, 'root-fill', 8))
    cards.append(drawing.txt(23, 39, core['name'], 'root-title'))
    cards.append(drawing.txt(23, 58, core['label'], 'root-desc'))
    centers = []
    for j, paper in enumerate(papers):
        title = drawing.wrap(paper['name'], 183, 15.8)
        copy = drawing.wrap(paper['method'], 315, 14.2)
        center = y + 18
        centers.append(center)
        wires.extend([drawing.path(f'M19 {center}H33', f'leaf-wire {palette}'),
                      drawing.dot(33, center, palette)])
        y = center + 16 + 22 * (len(title) - 1) + 21 * len(copy) + 10
        hitbox = f'<path class="tree-hitbox" d="M34 {center-24}H365V{y-7}H34Z" fill="transparent" aria-hidden="true"/>'
        item = hitbox + drawing.block(43, center + 2, title, 22, 'paper-title')
        item += drawing.txt(354, center + 1, paper.get('date') or '日期待核', 'date', end=True)
        item += drawing.block(43, center + 24 + 22 * (len(title) - 1), copy, 21, 'paper-copy')
        cards.append(drawing.paper_link(paper, item, 'paper'))
        if j < len(papers) - 1:
            wires.append(drawing.path(f'M43 {y - 2}H354'))
    wires.append(drawing.path(f'M19 {root_bottom}V{centers[-1]}', f'leaf-wire {palette}'))
    return drawing.rect(0, 0, width, y, 'bg') + ''.join(wires + cards), width, y


def chapter_svg(topic, branch, number, variant, *, standalone=False):
    papers = drawing.paper_rows(branch['papers'], 5)
    core = topic['core']
    entry_label = topic.get('entry_label', '论文')
    if variant == 'wide':
        content, width, height = wide_body(core, papers, number, entry_label)
    else:
        content, width, height = narrow_body(core, papers, number)
    xml = TEMPLATE.replace('viewBox="0 0 1920 1080"', f'viewBox="0 0 {width} {height}"')
    svg = ET.fromstring(Template(xml).substitute(
        title=escape(branch['title']),
        description=escape(f'{core["name"]} 直接连接本章{entry_label}，按日期从上到下排列。'),
        content=content))
    return format_svg(svg, branch['id'], variant, [p['id'] for p in papers], standalone)


def render_method_tree(topic, branch, number):
    cid = branch['id']
    label = escape(topic.get('entry_label', '论文'))
    return f'''<figure class="method-tree" aria-labelledby="tree-{cid}-caption">
<figcaption id="tree-{cid}-caption"><strong>本章方法树</strong><span>按日期从上到下排列，点击{label}跳到正文。</span></figcaption>
{chapter_svg(topic, branch, number, 'wide')}
{chapter_svg(topic, branch, number, 'narrow')}
</figure>'''


TREE_TEXT_CSS = """
.tree-narrow .paper-title{font-size:15.8px}
.tree-narrow .paper-copy{font-size:14.2px}
.tree-narrow .root-title{font-size:22px}
.tree-narrow .root-desc{font-size:12.8px}
.tree-map .date{font-size:14px}
.tree-narrow .date{font-size:13.3px}
.tree-map a.paper{cursor:pointer}
.tree-map .tree-hitbox{pointer-events:all}
.tree-original text{fill:var(--accent,var(--eyebrow));text-decoration:underline}
"""


TREE_CSS = scoped_template_css() + TREE_TEXT_CSS + """
.page .method-tree{margin:1.05rem 0 1.45rem}
.page .method-tree figcaption{display:flex;flex-wrap:wrap;align-items:baseline;gap:.12rem .78rem;
 margin:0 0 .48rem;padding:0;border:0;line-height:1.5;color:var(--ink)}
.method-tree figcaption strong{font-size:.94rem}
.method-tree figcaption>span{font-size:.81rem;color:var(--muted)}
.page .method-tree .tree-map{display:block;width:100%;height:auto;max-width:none;border:1px solid var(--line);border-radius:5px}
.page .method-tree .tree-narrow{display:none}
@media screen and (max-width:950px){
 .page .method-tree .tree-wide{display:none}
 .page .method-tree .tree-narrow{display:block;background:var(--bg)}
}
@media screen and (min-width:520px) and (max-width:950px){
 .page .method-tree .tree-narrow{max-height:35rem}
}
@media print{.method-tree{break-inside:avoid}}
"""
