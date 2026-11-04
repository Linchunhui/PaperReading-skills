#!/usr/bin/env python3
"""Normalize supplied text/parser JSON/skill outputs without fetching or parsing PDFs."""
import argparse
import hashlib
import json
from pathlib import Path

SKIP_FIELDS = {'evidence','upstream_evidence','paper_id','document_version_id','coverage','status','asset_ids','assets','identity_note'}


def normalize(raw, paper_id=None, document_version_id=None, coverage=None):
    if isinstance(raw,dict) and raw.get('schema_version') == '1.0' and isinstance(raw.get('papers'),list) and all('units' in p for p in raw['papers']):
        if paper_id is not None or document_version_id is not None or coverage is not None:
            raise ValueError('Input is already normalized; explicit overrides would change provenance. Edit its declared identity/coverage deliberately before normalization.')
        return raw
    if isinstance(raw,dict) and isinstance(raw.get('papers'),list):
        records = raw['papers']
        options = raw.get('options',{})
    elif isinstance(raw,dict) and isinstance(raw.get('paper'),dict):
        records = [raw['paper']]
        options = raw.get('options',{})
    else:
        records, options = [raw], {}
    if len(records)>1 and (paper_id or document_version_id):
        raise ValueError('ID overrides are only supported for a single paper')
    papers=[]
    for i,record in enumerate(records):
        meta=record if isinstance(record,dict) else {}
        digest=hashlib.sha256(json.dumps(record,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:12]
        pid=paper_id or meta.get('paper_id') or f'local-{digest}'
        vid=document_version_id or meta.get('document_version_id') or f'input-{digest}'
        units=[]
        local_identity=not(meta.get('paper_id') or paper_id) or not(meta.get('document_version_id') or document_version_id)
        def structured(value,pointer='',inherited=None):
            inherited=inherited or []
            if isinstance(value,dict):
                refs=value.get('evidence',inherited)
                for key,item in value.items():
                    if key not in SKIP_FIELDS:
                        esc=key.replace('~','~0').replace('/','~1')
                        structured(item,f'{pointer}/{esc}',refs)
            elif isinstance(value,list):
                for j,item in enumerate(value): structured(item,f'{pointer}/{j}',inherited)
            elif value is not None:
                text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,sort_keys=True)
                if text:
                    unit={'unit_id':pointer or '/','text':text,'origin':'structured','locator':{'json_pointer':pointer or '/'}}
                    if inherited: unit['upstream_evidence']=inherited
                    units.append(unit)
        if isinstance(record,str):
            units=[{'unit_id':'text-0001','text':record,'origin':'parsed_text','locator':{}}] if record else []
            inferred='partial'
        else:
            block_key=next((k for k in ['blocks','paragraphs','sections'] if isinstance(meta.get(k),list) and meta[k]),None)
            if block_key:
                for j,block in enumerate(meta[block_key]):
                    if not isinstance(block,dict) or not isinstance(block.get('text'),str) or not block['text']:
                        raise ValueError(f'{block_key}[{j}] requires nonempty text; use explicit structured normalization for a different parser')
                    locator={k:block[k] for k in ['page','section','bbox','start','end','title'] if k in block}
                    locator['json_pointer']=f'/{block_key}/{j}/text'
                    units.append({'unit_id':str(block.get('block_id') or block.get('id') or f'{block_key}-{j+1:04d}'),'text':block['text'],'origin':'parsed_text','locator':locator})
                # Retain complementary parser fields rather than silently dropping references or metadata.
                for key,value in meta.items():
                    if key not in SKIP_FIELDS | {block_key,'blocks','paragraphs','sections','content_coverage','full_text_chars','parse_mode'}:
                        structured(value,f'/{key}')
                inferred='partial'
            else:
                structured(meta)
                inferred='structured_only'
        if not units: raise ValueError(f'No usable source units for {pid}')
        ids=[u['unit_id'] for u in units]
        if len(ids)!=len(set(ids)): raise ValueError(f'Duplicate unit IDs for {pid}; resolve parser identity before analysis')
        declared=coverage or meta.get('coverage') or meta.get('content_coverage') or inferred
        if declared not in ['full_text','partial','abstract_only','structured_only']:
            raise ValueError(f'Unsupported coverage value: {declared}; select an explicit --coverage')
        # A generated skill output cannot be promoted to full original text by copying its old coverage.
        if isinstance(raw,dict) and raw.get('skill') and all(u['origin']=='structured' for u in units):
            declared='structured_only'
        paper={'paper_id':pid,'document_version_id':vid,'coverage':declared,'units':units,'assets':meta.get('assets',[])}
        if local_identity: paper['identity_note']='Locally assigned input identifiers; not bibliographic identifiers.'
        papers.append(paper)
    return {'schema_version':'1.0','papers':papers,'options':options}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('--paper-id')
    p.add_argument('--document-version-id')
    p.add_argument('--coverage',choices=['full_text','partial','abstract_only','structured_only'])
    a=p.parse_args()
    if a.input.suffix.lower()=='.pdf': p.error('Provide parser output or text, not PDF')
    text=a.input.read_text(encoding='utf-8')
    raw=json.loads(text) if a.input.suffix.lower()=='.json' else text
    try: result=normalize(raw,a.paper_id,a.document_version_id,a.coverage)
    except ValueError as e: p.error(str(e))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Normalized {len(result["papers"])} paper record(s) into {a.output}')

if __name__=='__main__': main()
