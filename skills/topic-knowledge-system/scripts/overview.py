#!/usr/bin/env python3
"""Render an evidence-backed topic as a self-contained 1920 × 1080 SVG."""
from argparse import ArgumentParser
from datetime import date
from html import escape
import json
from pathlib import Path
import re
from string import Template
from unicodedata import east_asian_width
from urllib.parse import urlsplit
from source_links import source_url

WIDTH, HEIGHT = 1920, 1080
BRANCH_X, BRANCH_W, PAPER_X, RIGHT, TRUNK = 280, 238, 571, 1878, 246
ASSET = Path(__file__).resolve().parents[1] / 'assets/tree.svg'


def required(obj, key):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'缺少文本字段 {key}')
    return value.strip()


def paper_rows(items, maximum):
    if not isinstance(items, list) or len(items) > maximum:
        raise ValueError(f'论文列表最多 {maximum} 项')
    for item in items:
        required(item, 'name')
        required(item, 'method')
        if item.get('date'):
            raw_date = item['date']
            if not isinstance(raw_date, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw_date):
                raise ValueError(f'{item["name"]} 的日期须为 YYYY-MM-DD')
            date.fromisoformat(raw_date)
        if item.get('url'):
            source_url(item['url'])
    return sorted(items, key=lambda p: p.get('date') or '9999')


def units(text):
    return sum(1.04 if ord(c) > 127 and east_asian_width(c) in 'FWA' else .61 for c in text)


def wrap(text, width, size):
    limit = (width - 8) / size
    rows, current = [], ''
    for word in re.findall(r'[A-Za-z0-9][A-Za-z0-9+./_-]*|[\s\S]', text):
        if units(word) > limit:
            raise ValueError(f'词组过长，请缩短显示名称：{word}')
        if current and units(current + word) > limit and word not in '，。；、！？）':
            rows.append(current.rstrip())
            current = ''
        if current or not word.isspace():
            current += word
    if current:
        rows.append(current.rstrip())
    return rows


def txt(x, y, content, cls, end=False):
    anchor = ' text-anchor="end"' if end else ''
    return f'<text x="{x:.2f}" y="{y:.2f}" class="{cls}"{anchor}>{escape(content)}</text>'


def block(x, y, rows, step, cls):
    return ''.join(txt(x, y + i * step, row, cls) for i, row in enumerate(rows))


def rect(x, y, w, h, color, radius=0):
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{w}" height="{h:.2f}" rx="{radius}" fill="var(--{color})"/>'


def path(d, cls='separator'):
    return f'<path class="{cls}" d="{d}"/>'


def dot(x, y, color):
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.7" fill="var(--{color})"/>'


def paper_link(p, content, cls):
    if not p.get('url'):
        return f'<g class="{cls}">{content}</g>'
    return f'<a class="{cls}" href="{escape(p["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{content}</a>'


def render(topic):
    title, subtitle = required(topic, 'title'), required(topic, 'subtitle')
    entry_label = topic.get('entry_label', '论文')
    date_label = topic.get('date_label', '首次提交日')
    if len(wrap(title, 1320, 47)) != 1 or len(wrap(subtitle, 1270, 17)) != 1:
        raise ValueError('请缩短标题或副标题')
    core = topic['core']
    core_name, core_label = required(core, 'name'), required(core, 'label')
    core_lines = wrap(required(core, 'description'), 143, 13.5)
    if len(wrap(core_name, 145, 35)) > 1 or len(wrap(core_label, 145, 15.5)) > 1 or len(core_lines) > 3:
        raise ValueError('核心方法名称或描述过长')
    background = paper_rows(topic.get('background', []), 4)
    branches = topic['branches']
    if not isinstance(branches, list) or not 1 <= len(branches) <= 6:
        raise ValueError('单张图支持 1–6 条问题分支')
    surface = [rect(0, 0, WIDTH, HEIGHT, 'bg')]
    wires, labels = [], []
    labels += [txt(42, 29, '专题知识图谱', 'eyebrow'), txt(39, 74, title, 'title'),
               txt(42, 103, subtitle, 'subtitle'), txt(RIGHT, 82, f'日期为{date_label}', 'foot', end=True)]
    wires.append(path(f'M42 112H{RIGHT}'))

    lineage = topic.get('lineage', '')
    if background or lineage:
        if lineage and len(wrap(lineage, 1250, 14)) != 1:
            raise ValueError('请缩短传承说明')
        panel_h = 98 if background else 34
        surface.append(rect(42, 123, RIGHT - 42, panel_h, 'preface', 10))
        if background:
            labels.append(txt(56, 145, '前序工作与应用 · 按日期排列', 'preface-title'))
        if lineage:
            labels.append(txt(RIGHT - 14, 145, '算法脉络  ' + lineage, 'preface-title', end=True))
        for i, paper in enumerate(background):
            x = 56 + i * 456
            if i:
                wires.append(path(f'M{x-18} 152V210'))
            method = wrap(paper['method'], 410, 14.4)
            if len(wrap(paper['name'], 300, 18)) != 1 or len(method) > 2:
                raise ValueError(f'请缩短背景条目 {paper["name"]}')
            card = txt(x, 170, paper['name'], 'context-name') + txt(x + 418, 169, paper.get('date') or '日期待核', 'date', end=True)
            labels.append(paper_link(paper, card + block(x, 194, method, 17, 'context-desc'), 'context'))
        top = 254 if background else 194
    else:
        top = 150

    layout = []
    total_papers = len(background)
    for branch in branches:
        name = required(branch, 'title')
        papers = paper_rows(branch['papers'], 5)
        if not papers or len(wrap(name, BRANCH_W - 55, 20)) != 1:
            raise ValueError(f'分支需有论文，且标题须放进一行：{name}')
        total_papers += len(papers)
        q = wrap(required(branch, 'description'), BRANCH_W - 32, 15.4)
        width = min(660 if len(papers) == 1 else 600, (RIGHT - PAPER_X - (len(papers)-1)*16)//len(papers))
        methods = [(p, wrap(p['method'], width - 9, 14.8)) for p in papers]
        if any(len(wrap(p['name'], width - 4, 17.5)) > 1 for p in papers):
            raise ValueError(f'请使用较短的论文显示名：{name}')
        note = branch.get('note', '')
        if note and len(wrap(note, RIGHT - PAPER_X, 13)) != 1:
            raise ValueError(f'请缩短分支备注：{name}')
        qh = 49 + 20*(len(q)-1)
        mh = 89 + 18.5*(max(len(lines) for _, lines in methods)-1)
        layout.append((name, q, qh, width, methods, note, max(qh + 12, mh) + (19 if note else 0)))
    free = 1023 - top - sum(row[-1] for row in layout)
    if free < 0:
        raise ValueError('内容放不进 16:9，请压缩描述或把问题组拆成两张图')
    gap = min(18, free / len(layout))
    labels += [txt(RIGHT, 51, f'{len(branches)} 条问题分支  /  {total_papers} 项{entry_label}', 'stats', end=True),
               txt(42, top-9, '核心方法', 'col-label'), txt(BRANCH_X, top-9, '问题分支', 'col-label'),
               txt(PAPER_X, top-9, f'{entry_label}与解决思路', 'col-label')]
    wires.append(path(f'M42 {top}H{RIGHT}'))
    y, centers = top, []
    for i, (name, q, qh, width, methods, note, row_h) in enumerate(layout, 1):
        height = row_h + gap
        center, bus_y = y + height/2, y + 13
        centers.append(center)
        qtop = center - qh/2
        surface.append(rect(BRANCH_X, qtop, BRANCH_W, qh, f'branch-{i}-fill', 9))
        card = txt(BRANCH_X+14, qtop+22, f'{i:02}', 'index')
        card += txt(BRANCH_X+45, qtop+23, name, 'question-title')
        card += block(BRANCH_X+14, qtop+44, q, 20, 'question-copy')
        labels.append(f'<g class="branch-{i}" aria-label="{escape(name, quote=True)}">{card}</g>')
        wires.append(path(f'M{TRUNK} {center}H{BRANCH_X}', f'branch-wire branch-{i}'))
        end = PAPER_X + 3 + (len(methods)-1)*(width+16)
        bx = BRANCH_X + BRANCH_W
        wires.append(path(f'M{bx} {center} C{bx+24} {center} {PAPER_X-38} {bus_y} {PAPER_X-14} {bus_y} H{end}',
                          f'leaf-wire branch-{i}'))
        for j, (paper, copy) in enumerate(methods):
            x = PAPER_X + j*(width+16)
            wires += [path(f'M{x+3} {bus_y}v9', f'leaf-wire branch-{i}'), dot(x+3, bus_y+9, f'branch-{i}')]
            if j:
                wires.append(path(f'M{x-8} {bus_y+24}V{y+height-10}'))
            card = txt(x, bus_y+30, paper['name'], 'paper-title')
            card += txt(x, bus_y+49, paper.get('date') or '日期待核', 'date')
            card += block(x, bus_y+69, copy, 18.5, 'paper-copy')
            labels.append(paper_link(paper, card, 'paper'))
        if note:
            labels.append(txt(PAPER_X, y+height-6, note, 'reading-note'))
        y += height
        wires.append(path(f'M{BRANCH_X} {y}H{RIGHT}'))

    middle = (centers[0] + centers[-1]) / 2
    rtop = middle - 61
    wires.append(path(f'M213 {middle}H{TRUNK} M{TRUNK} {centers[0]}V{centers[-1]}', 'trunk'))
    wires.extend(dot(TRUNK, cy, f'branch-{i}') for i, cy in enumerate(centers, 1))
    surface.append(rect(42, rtop, 171, 122, 'root-fill', 12))
    labels += [txt(56, rtop+35, core_name, 'root-title'), txt(56, rtop+57, core_label, 'root-desc'),
               block(56, rtop+78, core_lines, 16, 'root-copy')]
    labels += [txt(42, 1054, '同一横枝内从左到右按日期排列。', 'foot'),
               txt(RIGHT, 1054, '点击条目可打开原文', 'foot', end=True)]
    # Paint edges above the preface but below the nodes they connect.
    content = ''.join(surface[:2] + wires + surface[2:] + labels) if background or lineage else ''.join(surface[:1] + wires + surface[1:] + labels)
    description = f'{title}从左向右展开为{len(branches)}条问题分支，每条按日期排列相关资料与解法。'
    return Template(ASSET.read_text(encoding='utf-8')).substitute(
        title=escape(title), description=escape(description), content=content)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        topic = json.loads(args.input.read_text(encoding='utf-8'))
        svg = render(topic)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg, encoding='utf-8')
    except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        parser.exit(2, f'{exc}\n')


if __name__ == '__main__':
    main()
