"""Normalize parsed text or records; preserve source identity and provenance."""
from pathlib import Path
import argparse,copy,hashlib,json,re

def blocks(text,prefix='u'):
    return [{'unit_id':f'{prefix}{i+1:04d}','text':m.group(),'origin':'parsed_text',
             'locator':{'char_start':m.start(),'char_end':m.end(),'line_start':text[:m.start()].count('\n')+1}}
            for i,m in enumerate(re.finditer(r'\S[\s\S]*?(?=\n\s*\n|\Z)',text))]

def normalize(value,paper_id=None,version=None,coverage=None):
    if isinstance(value,str):
        pid=paper_id or 'local-paper';vid=version or 'text-sha256:'+hashlib.sha256(value.encode()).hexdigest()
        return {'schema_version':'1.0','papers':[{'paper_id':pid,'document_version_id':vid,'coverage':coverage or 'partial','units':blocks(value),'assets':[]}],'options':{}}
    value=copy.deepcopy(value)
    if isinstance(value,dict) and value.get('papers'):
        papers=value['papers'];options=value.get('options',{})
    elif isinstance(value,dict) and isinstance(value.get('units'),list):
        papers=[{**(value.get('paper') or value),'units':value['units']}];options=value.get('options',{})
    else:papers=[value];options={}
    result=[]
    for i,p in enumerate(papers):
        if not isinstance(p,dict):p={'data':p}
        pid=p.get('paper_id') or paper_id or f'local-paper-{i+1}'
        vid=p.get('document_version_id') or version or 'input-sha256:'+hashlib.sha256(json.dumps(p,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        cov=coverage or p.get('coverage') or 'partial'
        units=p.get('units')
        if not units and isinstance(p.get('pages'),list):
            units=[]
            for n,page in enumerate(p['pages']):
                page_no=page.get('page',page.get('page_number'))
                text=page.get('markdown')
                if not isinstance(text,str) or not text.strip():text=page.get('text','')
                text=text if isinstance(text,str) else ''
                current=blocks(text,prefix=f'page{n+1:04d}-u') if text.strip() else []
                for unit in current:
                    unit['origin']=page.get('origin','parsed_text')
                    if page.get('source_type'):unit['source_type']=page['source_type']
                # A page's untyped aggregate is not an independent primary
                # source for text explicitly marked upstream/reviewer in blocks.
                # Preserve data, but inherit those restrictions on duplicates.
                if 'origin' not in page and 'source_type' not in page:
                    for block in page.get('blocks',[]):
                        if not isinstance(block,dict):continue
                        bt=block.get('text',block.get('markdown'))
                        origin=block.get('origin');role=block.get('source_type')
                        if not isinstance(bt,str) or not bt.strip():continue
                        if origin!='structured' and role in (None,'paper'):continue
                        for unit in current:
                            if bt in unit['text'] or unit['text'] in bt:
                                unit['origin']='structured' if origin=='structured' else unit['origin']
                                unit['source_type']='structured' if origin=='structured' else role
                for j,block in enumerate(page.get('blocks',[])):
                    if not isinstance(block,dict):block={'value':block}
                    bt=block.get('text',block.get('markdown'))
                    if isinstance(bt,str) and bt.strip():
                        # Do not lose an independently typed block even when a
                        # page-level representation contains the same wording.
                        if bt in text and not {'origin','source_type'}&set(block):continue
                        u={'unit_id':block.get('unit_id',block.get('block_id',f'page{n+1:04d}-b{j+1:04d}')),
                           'text':bt,'origin':block.get('origin',page.get('origin','parsed_text')),
                           'locator':copy.deepcopy(block.get('locator',{}))}
                        role=block.get('source_type',page.get('source_type'))
                        if role:u['source_type']=role
                        current.append(u)
                    elif block:
                        current.append({'unit_id':block.get('unit_id',block.get('block_id',f'page{n+1:04d}-b{j+1:04d}')),
                                        'text':json.dumps(block,ensure_ascii=False,sort_keys=True),'origin':'structured',
                                        'source_type':'structured','locator':{'json_pointer':f'/pages/{n}/blocks/{j}'}})
                for unit in current:
                    if page_no is not None:unit['locator']['page']=page_no
                units.extend(current)
        if not units:
            # Keep the complete structured record; do not cherry-pick fields or
            # silently promote an upstream generation to original paper text.
            units=[{'unit_id':'structured-record','text':json.dumps(p,ensure_ascii=False,sort_keys=True),
                    'origin':'structured','source_type':'structured','locator':{'json_pointer':'/'}}]
            cov='structured_only'
        seen=set()
        for j,u in enumerate(units):
            u.setdefault('unit_id',f'u{j+1:04d}');u.setdefault('origin','parsed_text');u.setdefault('locator',{})
            if not isinstance(u.get('text'),str) or not u['text']:raise ValueError('Unit text must be nonempty')
            if u['unit_id'] in seen:raise ValueError('Duplicate unit ID: '+u['unit_id'])
            seen.add(u['unit_id'])
        result.append({'paper_id':pid,'document_version_id':vid,'coverage':cov,'units':units,'assets':p.get('assets',[])})
    return {'schema_version':'1.0','papers':result,'options':options}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');ap.add_argument('--paper-id');ap.add_argument('--version');ap.add_argument('--coverage',choices=['full_text','partial','abstract_only','structured_only','reviews_only']);a=ap.parse_args()
    path=Path(a.input);text=path.read_text();value=json.loads(text) if path.suffix.lower()=='.json' else text
    result=normalize(value,a.paper_id,a.version,a.coverage);Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
