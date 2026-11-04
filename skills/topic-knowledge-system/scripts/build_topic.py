#!/usr/bin/env python3
"""Build a self-contained topic report and optionally export its SVG trees."""

from argparse import ArgumentParser
from base64 import b64encode
from html import escape
import json
from pathlib import Path
import re
import struct
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from chapter_trees import TREE_CSS, chapter_svg, render_method_tree
from overview import paper_rows, render as render_overview, required

ASSETS = Path(__file__).resolve().parents[1] / 'assets'
COLORS = ('#246452', '#89553d', '#3c6086', '#735884', '#775d24', '#526d42')


def sequence(obj, key):
    value = obj.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f'{key} 须为数组')
    return value


def source_url(url):
    p = urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password:
        raise ValueError(f'来源须为 HTTPS 地址：{url}')
    return url


def link(url, label):
    return f'<a href="{escape(source_url(url), quote=True)}" target="_blank" rel="noopener noreferrer">{escape(label)} ↗</a>'


def register_id(record, used):
    item = required(record, 'id')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', item) or item in used:
        raise ValueError(f'ID 须唯一且只用小写字母、数字和连字符：{item}')
    used.add(item)


def svg_data(svg):
    return 'data:image/svg+xml;base64,' + b64encode(svg.encode()).decode('ascii')


def paragraphs(lines):
    return ''.join(f'<p>{escape(line)}</p>' for line in lines)


def optional_text(obj, key, css=''):
    value = obj.get(key)
    return f'<p class="{css}">{escape(value)}</p>' if value else ''


def svg_figure(item, input_dir):
    relative = Path(required(item, 'file'))
    file = (input_dir / relative).resolve()
    if relative.is_absolute() or not file.is_relative_to(input_dir) or file.suffix.lower() != '.svg':
        raise ValueError('figures.file 必须是输入 JSON 目录下的相对 SVG 路径')
    raw = file.read_text(encoding='utf-8')
    root = ET.fromstring(raw)
    if root.tag != '{http://www.w3.org/2000/svg}svg' or not root.get('viewBox'):
        raise ValueError(f'SVG 须有 viewBox：{relative}')
    for node in root.iter():
        if node.tag.split('}')[-1].lower() in {'script', 'foreignobject'}:
            raise ValueError(f'SVG 含活动内容：{relative}')
        for key, value in node.attrib.items():
            local = key.split('}')[-1].lower()
            if local.startswith('on') or (local in {'href', 'src'} and not value.startswith(('#', 'data:image/'))):
                raise ValueError(f'SVG 含活动或外部资源：{relative}')
    css_urls = re.findall(r'url\(([^)]*)\)', raw, re.I)
    if re.search(r'@import', raw, re.I) or any(not url.strip().strip(chr(34)+chr(39)).startswith('#')
                                            for url in css_urls):
        raise ValueError(f'SVG 含外部样式资源：{relative}')
    caption = escape(required(item, 'caption'))
    if item.get('url'):
        caption += ' ' + link(item['url'], item.get('locator') or '图源')
    return f'<figure class="inline-figure"><img src="{svg_data(raw)}" alt="{escape(required(item,"alt"), quote=True)}"><figcaption>{caption}</figcaption></figure>'


def original_figure_pdf(url, page):
    if re.search(r'[\x00-\x1f\x7f\\]', url):
        raise ValueError('论文原图的 PDF 链接含非法字符')
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        source_url(url)
    elif parsed.path.startswith('/') or not parsed.path.lower().endswith('.pdf') or parsed.query:
        raise ValueError('论文原图的 PDF 须为相对本地路径或 HTTPS 地址')
    fragment = f'page={page}'
    if parsed.fragment not in ('', fragment):
        raise ValueError('论文原图的 PDF 链接页码与 page 不一致')
    return parsed._replace(fragment=fragment).geturl()


def original_figure(item, input_dir, paper, index):
    relative = Path(required(item, 'file'))
    file = (input_dir / relative).resolve()
    if relative.is_absolute() or not file.is_relative_to(input_dir) or file.suffix.lower() != '.png':
        raise ValueError('original_figures.file 须为输入 JSON 目录下的相对 PNG 路径')
    raw = file.read_bytes()
    if len(raw) < 24 or raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[12:16] != b'IHDR':
        raise ValueError(f'论文原图须为有效 PNG：{relative}')
    width, height = struct.unpack('>II', raw[16:24])
    reading_width = item.get('reading_width', min(width, 1024))
    page = item.get('page')
    label = item.get('figure')
    if (type(page) is not int or page < 1 or not width or not height
            or type(reading_width) is not int or reading_width < 1):
        raise ValueError('论文原图的页码与图像尺寸须为正整数')
    if not ((type(label) is int and label > 0) or (isinstance(label, str) and label.strip())):
        raise ValueError('论文原图须保留原始图号')
    pdf = escape(original_figure_pdf(required(item, 'pdf'), page), quote=True)
    key = f'paper-figure:{paper["id"]}:{index}'
    alt = escape(required(item, 'alt'), quote=True)
    caption = escape(required(item, 'caption'))
    title = escape(f'{paper["name"]} · 原文图 {label}')
    data = b64encode(raw).decode('ascii')
    return f"""<figure class="original-figure" style="--reading-width:{reading_width}px;--native-width:{width}px" aria-labelledby="{key}-title">
<div class="original-figure-head"><strong id="{key}-title">{title}</strong>
<button type="button" class="figure-zoom" aria-controls="{key}-art" aria-pressed="false">放大原图</button></div>
<div id="{key}-art" class="original-art" aria-label="原图，放大后可滚动查看">
<img src="data:image/png;base64,{data}" width="{width}" height="{height}" loading="lazy" decoding="async" alt="{alt}"></div>
<figcaption>{caption} <a href="{pdf}" target="_blank" rel="noopener noreferrer">PDF 第 {page} 页 ↗</a></figcaption></figure>"""


MATH_NS = '{http://www.w3.org/1998/Math/MathML}'
MATH_TAGS = set('math mrow mi mn mo mtext mspace mfrac msqrt mroot msup msub msubsup mover munder munderover mtable mtr mtd'.split())
MATH_ATTRIBUTES = set('display mathvariant stretchy fence separator width height depth columnalign rowalign'.split())


def mathml(markup):
    root = ET.fromstring(markup)
    if root.tag not in ('math', MATH_NS + 'math'):
        raise ValueError('公式须以 math 元素开头')
    for node in root.iter():
        tag = node.tag.removeprefix(MATH_NS)
        if tag not in MATH_TAGS or any(key not in MATH_ATTRIBUTES for key in node.attrib):
            raise ValueError('公式仅支持常见 MathML 元素和排版属性')
        node.tag = tag
    root.set('display', 'block')
    return ET.tostring(root, encoding='unicode')


def supplementary(obj, input_dir):
    equations = []
    for formula in sequence(obj, 'formulas'):
        note = optional_text(formula, 'explain', 'math-note')
        content = (mathml(required(formula, 'mathml')) if 'mathml' in formula else
                   f'<code>{escape(required(formula,"expression"))}</code>')
        equations.append(f'<aside class="equation">{content}{note}</aside>')
    return ''.join(equations) + ''.join(svg_figure(item, input_dir) for item in sequence(obj, 'figures'))


def experiments(entry):
    results = sequence(entry, 'results')
    if not results:
        return ''
    rows = []
    for row in results:
        baseline = row.get('baseline', '')
        change = row.get('change', '')
        if change and not baseline:
            raise ValueError('没有明确可比基线的结果不得填写差值')
        result = escape(required(row, 'result'))
        metric = escape(required(row, 'metric'))
        settings = escape(required(row, 'conditions'))
        evidence = link(row.get('url') or entry['url'], required(row, 'locator'))
        rows.append(f'<tr><td>{settings}<br><small>{evidence}</small></td><td>{metric}</td>'
                    f'<td>{escape(baseline or "—")}</td><td>{result}</td><td>{escape(change or "—")}</td></tr>')
    return f'''<section class="experiment"><h4>证据与结果</h4>
<div class="ve-table"><table><thead><tr><th scope="col">条件</th><th scope="col">指标</th>
<th scope="col">基线</th><th scope="col">结果</th><th scope="col">差值</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div></section>'''


def entry_html(entry, input_dir):
    date = entry.get('date')
    time = f'<time datetime="{date}">{date}</time>' if date else '<span class="source">日期待核</span>'
    steps = sequence(entry, 'steps')
    items = ''.join(f'<li>{escape(step)}</li>' for step in steps)
    walkthrough = f'<ol class="steps">{items}</ol>' if items else ''
    evidence = []
    for item in sequence(entry, 'evidence'):
        citation = link(item.get('url') or entry['url'], required(item, 'locator'))
        evidence.append(f'<li>{escape(required(item,"text"))} {citation}</li>')
    details = f'<details class="evidence"><summary>证据与原文定位</summary><ul>{"".join(evidence)}</ul></details>' if evidence else ''
    originals = ''.join(original_figure(item, input_dir, entry, index)
                        for index, item in enumerate(sequence(entry, 'original_figures'), 1))
    return f'''<article class="paper" id="paper-{entry['id']}">
<div class="paper-label"><h3>{escape(entry.get('title') or entry['name'])}</h3>{time}</div>
<p class="paper-goal">{escape(entry['method'])}</p>{walkthrough}
{supplementary(entry,input_dir)}{originals}{experiments(entry)}{optional_text(entry,"boundary","boundary")}
<p class="source">{link(entry['url'],entry.get('locator') or '原文')}</p>{details}</article>'''


def branch_html(topic, branch, number, input_dir):
    context = paragraphs(sequence(branch, 'context'))
    case = branch.get('case')
    baseline = f'<aside class="baseline-case"><h3>读图前的算例</h3><p>{escape(case)}</p></aside>' if case else ''
    entries = ''.join(entry_html(p, input_dir) for p in paper_rows(branch['papers'],5))
    return f'''<section class="chapter" id="{branch['id']}" style="--accent:{COLORS[number-1]}">
<header class="chapter-head"><span class="chapter-index" aria-hidden="true">{number:02}</span>
<div><p class="kicker">问题 {number:02}</p><h2>{escape(branch['title'])}</h2></div></header>
<p class="problem">{escape(branch['description'])}</p>{context}{baseline}
{render_method_tree(topic,branch,number)}{supplementary(branch,input_dir)}
{entries}{optional_text(branch,"synthesis","compare")}</section>'''


def build(topic, input_dir):
    used = {'top', 'overview', 'background', 'open-questions', 'map-frame', 'map-zoom'}
    branches = sequence(topic, 'branches')
    for branch in branches:
        register_id(branch, used)
        if branch['id'].startswith('paper-'):
            raise ValueError('章节 ID 不得使用 paper- 前缀')
        label = branch.get('label') or branch['title']
        for paper in sequence(branch, 'papers'):
            register_id(paper, used)
            source_url(required(paper, 'url'))
        if not branch['papers']:
            raise ValueError(f'问题「{label}」至少需要一个有来源的条目')

    overview = render_overview({**topic, 'branches': [
        {**b, 'title': b.get('label') or b['title']} for b in branches]})
    map_data = svg_data(overview)
    css = (ASSETS / 'report.css').read_text(encoding='utf-8') + TREE_CSS
    intro = paragraphs(sequence(topic, 'intro'))
    background = ''.join(
        f'<li><strong>{escape(p["name"])}</strong> {escape(p.get("date") or "日期待核")} · {escape(p["method"])} '
        f'{link(p["url"],"原文") if p.get("url") else ""}</li>'
        for p in paper_rows(sequence(topic, 'background'),4))
    preface = f'<section id="background" class="compare"><h2>前序与应用</h2><ul>{background}</ul></section>' if background else ''
    nav = ''.join(f'<a href="#{b["id"]}">{escape(b.get("label") or b["title"])}</a>' for b in branches)
    if preface:
        nav = '<a href="#background">前序与应用</a>' + nav
    chapters = ''.join(branch_html(topic,b,i,input_dir) for i,b in enumerate(branches,1))
    questions = ''.join(f'<li>{escape(q)}</li>' for q in sequence(topic, 'open_questions'))
    closing = f'<section id="open-questions" class="compare"><h2>待解决问题</h2><ul>{questions}</ul></section>' if questions else ''
    entries = sum(len(b['papers']) for b in branches)
    title = escape(topic['title'])
    subtitle = escape(topic['subtitle'])
    scope = optional_text(topic, 'scope', 'problem')
    count_label = escape(topic.get('entry_label', '论文'))

    html = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{css}</style></head><body><div class="page" id="top">
<header class="masthead"><div class="mastline"><p class="kicker">专题知识体系</p><span class="mast-tag">问题与证据</span></div>
<h1>{title}</h1><p class="deck">{subtitle}</p>
<dl class="report-index"><div><dt>问题分支</dt><dd>{len(branches):02}</dd></div><div><dt>项{count_label}</dt><dd>{entries}</dd></div></dl></header>
<nav class="toc" aria-label="章节"><div><a href="#overview">总览</a>{nav}</div></nav>
<main class="report-body">
<details class="map" id="overview" open><summary>专题问题树</summary>
<div class="mapbar"><button type="button" id="map-zoom" aria-pressed="false">放大图</button>
<a href="{map_data}" download="overview.svg">下载 SVG</a></div>
<figure class="topic-figure"><div class="mapframe" id="map-frame" tabindex="0" aria-label="专题总览，可横向滚动">
<img src="{map_data}" width="1920" height="1080" alt="{title}的专题问题树"></div>
<figcaption>问题树按章呈现问题与做法。章内小树提供逐项做法和原文入口。</figcaption></figure></details>
<div class="reader">{scope}{intro}{preface}{chapters}{closing}</div>
</main><footer><a href="#top">回到目录</a></footer></div>
<script>
const zoom = document.getElementById('map-zoom');
const frame = document.getElementById('map-frame');
zoom.addEventListener('click', () => {{
  const enlarged = frame.classList.toggle('zoom');
  zoom.setAttribute('aria-pressed', String(enlarged));
  zoom.textContent = enlarged ? '适应宽度' : '放大图';
}});
document.querySelectorAll('.figure-zoom').forEach(button => {{
  button.addEventListener('click', () => {{
    const art = document.getElementById(button.getAttribute('aria-controls'));
    const enlarged = art.classList.toggle('is-zoomed');
    button.setAttribute('aria-pressed', String(enlarged));
    button.textContent = enlarged ? '缩回版宽' : '放大原图';
    if (enlarged) art.tabIndex = 0;
    else {{
      art.removeAttribute('tabindex');
      art.scrollTo(0, 0);
    }}
  }});
}});
</script></body></html>'''
    return html, overview


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='topic.json')
    parser.add_argument('output', type=Path, help='输出 HTML 路径')
    parser.add_argument('--svg-dir', type=Path, help='可选，另存总览和各章宽屏、移动版 SVG')
    args = parser.parse_args()
    try:
        path = args.input.resolve()
        topic = json.loads(path.read_text(encoding='utf-8'))
        if path == args.output.resolve():
            raise ValueError('输入和输出须为不同文件')
        html, overview = build(topic, path.parent)
        if args.svg_dir:
            diagrams = {'overview.svg': overview}
            for i, branch in enumerate(topic['branches'],1):
                for variant in ('wide', 'narrow'):
                    diagrams[f'{branch["id"]}-{variant}.svg'] = chapter_svg(
                        topic,branch,i,variant,standalone=True)
            args.svg_dir.mkdir(parents=True,exist_ok=True)
            for name, svg in diagrams.items():
                (args.svg_dir / name).write_text(svg,encoding='utf-8')
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(html,encoding='utf-8')
    except (ValueError, KeyError, TypeError, AttributeError, OSError, ET.ParseError) as exc:
        parser.exit(2, f'{exc}\n')


if __name__ == '__main__':
    main()
