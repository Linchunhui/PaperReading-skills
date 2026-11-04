#!/usr/bin/env python3
"""Turn a UTF-8 text file into provenance-preserving assessment units; no LLM."""
import argparse
import hashlib
import json
from pathlib import Path
import re

SOURCE_TYPES = ['paper','prior_work','review','rebuttal','resource_check','execution_check','structured']
COVERAGES = ['full_text','partial','abstract_only','structured_only','reviews_only']

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('--paper-id', required=True)
    p.add_argument('--source-id', required=True)
    p.add_argument('--version', default='unversioned-input')
    p.add_argument('--source-type', choices=SOURCE_TYPES, default='paper')
    p.add_argument('--paper-type', action='append', default=[])
    p.add_argument('--coverage', choices=COVERAGES, default=None)
    p.add_argument('--dimension', action='append', default=[])
    p.add_argument('--coverage-note', action='append', default=[])
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.source.resolve() == a.output.resolve():
        p.error('Output must not replace the source file.')
    raw = a.source.read_bytes()
    # Keep line endings in the decoded source; quotes and character offsets remain exact.
    text = raw.decode('utf-8')
    units = []
    for part in re.finditer(r'\S[\s\S]*?(?=\r?\n[ \t]*\r?\n|\Z)', text):
        content = part.group().rstrip()
        if not content:
            continue
        units.append({'unit_id': f'u{len(units)+1:04d}', 'source_type': a.source_type, 'source_id': a.source_id, 'source_version': None if a.version=='unversioned-input' else a.version, 'text': content, 'locator': {'path': str(a.source.resolve()), 'source_sha256': hashlib.sha256(raw).hexdigest(), 'char_start': part.start(), 'char_end': part.start()+len(content)}})
    if not units:
        p.error('Source contains no non-whitespace text.')
    coverage = a.coverage or ('reviews_only' if a.source_type in ['review','rebuttal'] else 'structured_only' if a.source_type=='structured' else 'partial')
    notes = a.coverage_note or ['由提供的文本分段；正文、图表、附录及前作覆盖尚未独立确认。']
    result = {'schema_version':'1.0', 'papers':[{'paper_id':a.paper_id, 'document_version_id':a.version, 'paper_type':a.paper_type or ['未分类'], 'coverage':coverage, 'coverage_notes':notes, 'units':units}], 'options':{'dimension_ids':a.dimension,'target_context':None}}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'output':str(a.output),'units':len(units),'coverage':coverage}, ensure_ascii=False))

if __name__ == '__main__':
    main()
