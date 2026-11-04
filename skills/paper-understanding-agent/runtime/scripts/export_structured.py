"""Lossless evidence adapter for existing paper-structured-summary consumers."""
from pathlib import Path
import argparse,json
from validate_output import FIELDS

def export(inp,doc):
    papers=[]
    for p in doc['papers']:
        ev={e['evidence_id']:e for e in p['evidence']};facts={f['fact_id']:f for f in p['facts']}
        source=next(s for s in inp['papers'] if s['paper_id']==p['paper_id'] and s['document_version_id']==p['document_version_id'])
        units={u['unit_id']:u for u in source['units']}
        def evidence(fids):
            rows=[];seen=set()
            for fid in fids:
                for eid in facts[fid]['evidence_ids']:
                    if eid in seen:continue
                    e=ev[eid];rows.append({'paper_id':p['paper_id'],'document_version_id':p['document_version_id'],'unit_id':e['unit_id'],'quote':e['quote']});seen.add(eid)
            return rows
        data={f:[{'item_id':i['item_id'],'text':i['text'],'basis':i['basis'],'evidence':evidence(i['fact_ids'])} for i in p['understanding'][f]] for f in FIELDS}
        data['problem_signatures']=[{**{k:v for k,v in s.items() if k!='fact_ids'},'evidence':evidence(s['fact_ids'])} for s in p['understanding']['problem_signatures']]
        data['missing_fields']=[{'path':m['path'],'reason':m['reason'],'detail':m['detail']} for m in p['missing_information'] if m['reason']!='not_requested']
        coverage=p['coverage'] if p['coverage']!='reviews_only' else 'partial'
        limits=list(p['limitations'])
        roles={}
        for e in ev.values():
            u=units[e['unit_id']]
            role='structured' if u.get('origin')=='structured' else u.get('source_type','paper')
            if role!='paper':roles[e['unit_id']]=role
        if roles:limits.append('旧契约不承载逐条来源类型；证据单元来源：'+json.dumps(roles,ensure_ascii=False,sort_keys=True)+'。不得将其统一视为本文原文。')
        if p['coverage']=='reviews_only':limits.append('原始coverage=reviews_only；旧契约仅表示为partial，来源类型保存在主结果。')
        papers.append({'paper_id':p['paper_id'],'document_version_id':p['document_version_id'],'coverage':coverage,'status':'complete' if coverage=='full_text' and p['processing_status']=='complete' else 'partial','data':data,'limitations':limits})
    return {'schema_version':'1.0','skill':'paper-structured-summary','papers':papers}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');ap.add_argument('legacy');a=ap.parse_args()
    inp=json.loads(Path(a.input).read_text());doc=json.loads(Path(a.output).read_text())
    Path(a.legacy).write_text(json.dumps(export(inp,doc),ensure_ascii=False,indent=2)+'\n')
