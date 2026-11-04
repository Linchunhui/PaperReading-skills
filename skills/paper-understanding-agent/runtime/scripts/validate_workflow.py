"""Scope and stage invariants for the complete paper workflow (not semantic grading)."""
import hashlib
import json
from collections import Counter

DIMS = {'B1', 'B2', 'B3', 'V1', 'Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6'}
SINGLES = {'metadata', 'understanding', 'assessment', 'reading', 'references'}

def input_digest(inp):
    raw = json.dumps(inp, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()

def fact_refs(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {'fact_ids', 'supporting_fact_ids', 'counter_fact_ids'}:
                yield from value
            else:
                yield from fact_refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from fact_refs(item)

def validate_workflow(inp, out):
    errors = []
    if len(inp['papers']) != 1 or len(out['papers']) != 1:
        return ['Complete workflow processes one paper per manifest']
    p = out['papers'][0]
    source = inp['papers'][0]
    units = {u['unit_id']: u for u in source['units']}
    w = p['workflow']; scope = w['scope']; stages = w['stages']
    main = set(scope['main_unit_ids']); refs = set(scope['reference_unit_ids'])
    metadata_only = set(scope.get('metadata_unit_ids', []))
    external = set(scope['external_unit_ids'])
    excluded = [x['unit_id'] for x in scope['excluded_units']]
    unresolved = [x['unit_id'] for x in scope['unresolved_units']]
    assignments = scope['main_unit_ids'] + scope.get('metadata_unit_ids', []) + scope['reference_unit_ids'] + scope['external_unit_ids'] + excluded + unresolved
    if Counter(assignments) != Counter(units.keys()):
        errors.append('Scope must partition every input unit exactly once')
    if w['input_sha256'] != input_digest(inp):
        errors.append('Workflow input hash mismatch')
    by_kind = {kind: [s for s in stages if s['kind'] == kind] for kind in SINGLES | {'page', 'section'}}
    if len({s['stage_id'] for s in stages}) != len(stages):
        errors.append('Duplicate stage_id')
    for kind in SINGLES:
        if len(by_kind[kind]) != 1:
            errors.append('Required singleton stage missing or repeated: ' + kind)
    for s in stages:
        if (s['paper_id'], s['document_version_id']) != (p['paper_id'], p['document_version_id']):
            errors.append('Stage paper/version mismatch: ' + s['stage_id'])
        if s['input_sha256'] != w['input_sha256']:
            errors.append('Stage input hash mismatch: ' + s['stage_id'])
        if not set(s['source_unit_ids'] + s['context_unit_ids']) <= units.keys():
            errors.append('Unknown stage source unit: ' + s['stage_id'])
        if set(s['source_unit_ids']) & set(s['context_unit_ids']):
            errors.append('Owned/context unit overlap: ' + s['stage_id'])
        if s['kind'] in {'page', 'section'} and not set(s['source_unit_ids'] + s['context_unit_ids']) <= main:
            errors.append('Page/section stage leaks outside main body: ' + s['stage_id'])
        expected_scope = set(scope.get('metadata_source_unit_ids', list(main | metadata_only))) if s['kind'] == 'metadata' else main
        if s['kind'] in {'metadata', 'understanding'} and set(s['source_unit_ids']) != expected_scope:
            errors.append('Whole-body/metadata stage must cover its declared units: ' + s['stage_id'])
        if s['kind'] in {'assessment', 'reading'} and (not main <= set(s['source_unit_ids']) or not set(s['source_unit_ids'] + s['context_unit_ids']) <= main | external):
            errors.append('Assessment/reading scope must cover body and only declared external sources')
        if s['kind'] == 'references' and set(s['source_unit_ids']) != refs:
            errors.append('References stage must cover full reference region')
    for kind, field, id_key, group_field in [('page', 'page_extractions', 'page_id', 'pages'),
                                            ('section', 'section_summaries', 'section_id', 'sections')]:
        groups = scope[group_field]
        if len({g[id_key] for g in groups}) != len(groups):
            errors.append('Duplicate scope group: ' + kind)
        if Counter(u for g in groups for u in g['unit_ids']) != Counter(main):
            errors.append('Scope groups must cover body exactly once: ' + kind)
        expected = {g[id_key]: g['unit_ids'] for g in groups}
        actual = {g[id_key]: g['source_unit_ids'] for g in p[field]}
        if len(actual) != len(p[field]) or actual != expected:
            errors.append('Missing or mismatched page/section output: ' + kind)
        if Counter(tuple(s['source_unit_ids']) for s in by_kind[kind]) != Counter(tuple(g['unit_ids']) for g in groups):
            errors.append('Missing or mismatched page/section stage: ' + kind)
    partial = source['coverage'] != 'full_text' or unresolved or any(s['status'] == 'partial' for s in stages)
    if partial and p['processing_status'] != 'partial':
        errors.append('Incomplete source or stage cannot become complete')
    missing = {m['path'] for m in p['missing_information']}
    if any(m['reason'] == 'not_requested' for m in p['missing_information']):
        errors.append('Complete workflow cannot omit fields as not_requested')
    if main:
        for field in ['background', 'problem', 'approach', 'methods', 'results']:
            if not p['understanding'][field] and '/understanding/' + field not in missing:
                errors.append('Empty core understanding requires explicit source gap: ' + field)
        if not any(s['points'] for s in p['content_products']['deep_read']) and '/content_products/deep_read' not in missing:
            errors.append('Complete reading product is empty without an explicit source gap')
    for field in ['title', 'authors', 'affiliations', 'dates', 'venue', 'identifiers', 'resources', 'original_abstract', 'references']:
        if not p['metadata'][field] and '/metadata/' + field not in missing:
            errors.append('Empty metadata requires explicit reason: ' + field)
    if {a['dimension_id'] for a in p['assessments']} != DIMS:
        errors.append('Complete workflow requires all ten dimensions')
    if not set(p['assessment_summary']['assessment_refs']) <= DIMS:
        errors.append('Unknown aggregate assessment reference')
    ev = {e['evidence_id']: e for e in p['evidence']}
    facts = {f['fact_id']: f for f in p['facts']}
    fact_units = {fid: {ev[eid]['unit_id'] for eid in f['evidence_ids']} for fid, f in facts.items()}
    for s in stages:
        if not set(s['evidence_ids']) <= ev.keys():
            errors.append('Unknown stage evidence: ' + s['stage_id'])
        allowed = set(s['source_unit_ids'] + s['context_unit_ids'])
        for eid in s['evidence_ids']:
            if eid in ev and ev[eid]['unit_id'] not in allowed:
                errors.append('Stage evidence outside declared scope: ' + s['stage_id'])
        for fid in s['fact_ids']:
            if not fact_units[fid] <= allowed:
                errors.append('Stage fact outside declared scope: ' + s['stage_id'])
            if s['kind'] == 'page' and not fact_units[fid] & set(s['source_unit_ids']):
                errors.append('Page fact belongs only to context: ' + fid)
    def check_claim_scope(node, allowed, label):
        for fid in fact_refs(node):
            if not fact_units[fid] or not fact_units[fid] <= allowed:
                errors.append('Non-body evidence used in ' + label + ': ' + fid)
    for field in ['page_extractions', 'section_summaries']:
        for row in p[field]:
            check_claim_scope(row, main, field)
            if not row['summary'] and '/' + field not in missing:
                errors.append('Empty page/section summary requires missing-information entry')
    for field, value in p['understanding'].items():
        check_claim_scope(value, main | external if field == 'related_work' else main, 'understanding/' + field)
    for field in ['assessments', 'assessment_summary', 'recommendations', 'reuse_cards', 'insight_rules', 'glossary', 'display', 'content_products']:
        check_claim_scope(p[field], main | external, field)
    check_claim_scope({'fact_ids': p['metadata']['fact_ids']}, main | metadata_only, 'metadata')
    check_claim_scope(p['metadata']['resources'], main | metadata_only | external, 'metadata/resources')
    contributors = p['metadata'].get('contributors', [])
    if len({c['author_id'] for c in contributors}) != len(contributors):
        errors.append('Duplicate contributor identity')
    aff_ids = {a['affiliation_id'] for a in p['metadata']['affiliations']}
    for contributor in contributors:
        if not set(contributor['affiliation_ids']) <= aff_ids:
            errors.append('Unknown contributor affiliation')
    if p['metadata'].get('author_list_basis') == 'not_observed' and p['metadata']['authors']:
        errors.append('Unobserved author byline cannot contain inferred authors')
    spans = scope['original_abstract_spans']
    for span in spans:
        u = units.get(span['unit_id'])
        if (not u or span['unit_id'] not in main or u.get('origin') == 'structured'
                or span['quote'] not in u['text']):
            errors.append('Original abstract span lacks original body source')
    expected_abstract = '\n'.join(s['quote'] for s in spans) if spans else None
    if p['metadata']['original_abstract'] != expected_abstract:
        errors.append('Original abstract must copy ordered source spans verbatim')
    bibliography = p['metadata']['references']
    if len({r['reference_id'] for r in bibliography}) != len(bibliography):
        errors.append('Duplicate reference occurrence ID')
    accounted = set()
    positions = {uid: i for i, uid in enumerate(scope['reference_unit_ids'])}
    first_positions = []
    for r in bibliography:
        ids = set(r['source_unit_ids']); accounted.update(ids)
        if not ids <= refs:
            errors.append('Reference outside reference region: ' + r['reference_id'])
            continue
        check_claim_scope({'fact_ids': r['fact_ids']}, ids, 'reference/' + r['reference_id'])
        raw_source = ' '.join('\n'.join(units[u]['text'] for u in r['source_unit_ids']).split())
        if ' '.join(r['raw_citation'].split()) not in raw_source:
            errors.append('Reference raw citation is not a source substring: ' + r['reference_id'])
        order = [positions[u] for u in r['source_unit_ids']]
        if order != sorted(order):
            errors.append('Reference source order changed: ' + r['reference_id'])
        first_positions.append(order[0])
    if first_positions != sorted(first_positions):
        errors.append('Reference occurrence order changed')
    for key in ['unparsed_segments', 'excluded_segments']:
        for segment in p['bibliography'][key]:
            accounted.update(segment['unit_ids'])
            if not set(segment['unit_ids']) <= refs:
                errors.append('Bibliography segment outside reference region')
            elif ' '.join(segment['text'].split()) not in ' '.join('\n'.join(units[u]['text'] for u in segment['unit_ids']).split()):
                errors.append('Bibliography segment is not a source substring')
    if accounted != refs:
        errors.append('Reference units silently omitted or added')
    if p['bibliography']['unparsed_segments'] and (p['processing_status'] != 'partial' or any(s['status'] != 'partial' for s in by_kind['references'])):
        errors.append('Unparsed references require partial reference stage and record')
    return errors
