"""Render complete reading notes or an explicitly requested compact card."""
from pathlib import Path
import argparse,json
from validate_output import FIELDS

LABELS=dict(zip(FIELDS,['背景','方向','问题','思路','方法','总结','结果','边界']))
def join_sentences(values):
    """Retain source wording while avoiding punctuation such as '。；'."""
    result=''
    for value in dict.fromkeys(v for v in values if v):
        if result:result+=' ' if result[-1] in '。.!?！？；;' else '；'
        result+=value
    return result

def render_compact(doc):
    lines=[]
    for p in doc['papers']:
        lines+=['# '+(p['metadata']['title'] or p['paper_id']),'',p['display']['one_liner']['text'],'']
        selected=set(p['display']['highlight_item_ids']);seen=set()
        for field in FIELDS:
            for item in p['understanding'][field]:
                if item['item_id'] not in selected or item['text'] in seen:continue
                lines.append(f'- **{LABELS[field]}**：{item["text"]}');seen.add(item['text'])
        if p['display']['recommendation_ids']:
            lines+=['','值得关注：']
            reasons={r['reason_id']:r for r in p['recommendations']}
            for rid in p['display']['recommendation_ids']:
                r=reasons[rid];lines.append(f'- {r["label"]}：{r["text"]}')
                extra=[v for v in [r['scope'],r.get('caveat')] if v and v not in r['text']]
                if extra:lines.append('  适用与边界：'+join_sentences(extra))
        for c in p['reuse_cards']:
            lines+=['',f'可借鉴：{c["component"]}',f'最小验证：{c["minimal_check"]}']
            if c['prerequisites']:lines.append('前提：'+'；'.join(c['prerequisites']))
            if c['steps']:lines.append('操作：'+' → '.join(c['steps']))
            lines.append('验证状态：'+{'proposed_unrun':'建议，未执行','reported_transfer':'论文报告迁移','verified':'输入中有执行核验记录'}[c['verification_status']])
        if p.get('profile')!='comprehensive' and p['limitations']:
            lines+=['','材料范围：'+join_sentences(p['limitations'])]
        if p.get('processing_status')=='partial':
            lines+=['','材料有缺项，详见结构化记录。']
        lines+=['']
    return '\n'.join(lines)

def render_detailed(doc):
    lines=[]
    for p in doc['papers']:
        lines+=['# '+(p['metadata']['title'] or p['paper_id']),'']
        metadata=p['metadata']
        if metadata['authors']:
            lines+=['作者：'+'、'.join(a['name'] for a in metadata['authors']),'']
        if metadata['affiliations']:
            lines+=['机构：'+'；'.join(a['name'] for a in metadata['affiliations']),'']
        products=p.get('content_products',{})
        abstract=products.get('abstract',[])
        if abstract:
            lines+=['## 内容摘要','']
            lines.extend(c['text']+'\n' for c in abstract)
        else:
            lines+=[p['display']['one_liner']['text'],'']
        deep_read=products.get('deep_read',[])
        useful_sections=[s for s in deep_read if s.get('points')]
        if useful_sections:
            for section in useful_sections:
                lines+=['## '+section['section'],'']
                # A full explanation retains paragraphs and all supplied claims;
                # display.highlight_item_ids belongs only to the compact view.
                lines.extend(point['text']+'\n' for point in section['points'])
        else:
            headings={'background':'研究背景','direction':'研究范围','problem':'具体问题',
                      'approach':'解决思路','methods':'具体方法','results':'实验与结果',
                      'summary':'主要结论','reported_limitations':'适用边界'}
            for field in FIELDS:
                claims=p['understanding'][field]
                if claims:
                    lines+=['## '+headings[field],'']
                    lines.extend(c['text']+'\n' for c in claims)
        if p.get('assessment_summary'):
            lines+=['## 阅读价值','',p['assessment_summary']['summary']['text'],'']
        if p['recommendations']:
            lines+=['## 推荐理由','']
            for reason in p['recommendations']:
                lines+=['### '+reason['label'],'',reason['text'],'']
                scope=[v for v in [reason['scope'],reason.get('caveat')] if v and v not in reason['text']]
                if scope:lines+=['适用条件：'+join_sentences(scope),'']
        if p['reuse_cards']:
            lines+=['## 可以怎样借鉴','']
            for card in p['reuse_cards']:
                lines+=['### '+card['component'],'']
                if card['prerequisites']:lines+=['前提：'+'；'.join(card['prerequisites']),'']
                if card['steps']:lines+=[' → '.join(card['steps']),'']
                lines+=['最小验证：'+card['minimal_check'],'']
                if card['verification_status']=='proposed_unrun':lines+=['以上为待验证的迁移建议。','']
        # Stage limitations mix page ownership, run diagnostics and article
        # caveats. Keep the raw list in the record; the reading product explains
        # substantive boundaries with its own evidence-backed paragraphs.
        if p.get('processing_status')=='partial':
            lines+=['## 材料范围','','本次处理有缺项，详见结构化记录中的缺失项与阶段说明。','']
        elif p.get('profile')!='comprehensive' and p['limitations']:
            lines+=['## 材料范围','',join_sentences(p['limitations']),'']
    return '\n'.join(lines)

def render(doc,mode='auto'):
    if mode not in {'auto','detailed','compact'}:raise ValueError('Unknown reading mode: '+mode)
    # Keep v1 standard-mode callers stable. The unified comprehensive workflow
    # defaults to the complete reading product.
    if mode=='auto':
        mode='detailed' if any(p.get('profile')=='comprehensive' for p in doc['papers']) else 'compact'
    return render_detailed(doc) if mode=='detailed' else render_compact(doc)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');ap.add_argument('--mode',choices=['auto','detailed','compact'],default='auto');a=ap.parse_args()
    Path(a.output).write_text(render(json.loads(Path(a.input).read_text()),a.mode))
