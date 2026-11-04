#!/usr/bin/env python3
"""Check schema, exact source quotes and assessment invariants; not scientific truth."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE_KINDS = {
    'paper': {'author_claim','method','reported_result','limitation','resource_statement'},
    'prior_work': {'prior_work'}, 'review': {'review_opinion'}, 'rebuttal': {'author_response'},
    'resource_check': {'resource_verification'}, 'execution_check': {'execution_verification'},
    'structured': {'upstream_summary'},
}
DIRECT = {'paper','prior_work','resource_check','execution_check'}

def validate(source, output):
    try:
        import jsonschema
    except ImportError:
        raise RuntimeError('Missing jsonschema; install with: python -m pip install jsonschema')
    errors = []
    schema = json.loads((ROOT/'references/output.schema.json').read_text())
    for err in jsonschema.Draft202012Validator(schema).iter_errors(output):
        errors.append(f'output/{"/".join(map(str,err.absolute_path))}: {err.message}')
    if errors:
        return errors
    design = json.loads((ROOT/'references/dimensions.json').read_text())['dimensions']
    dimensions = {d['id']: d for d in design}
    wanted = source.get('options',{}).get('dimension_ids') or list(dimensions)
    if len(set(wanted)) != len(wanted) or not set(wanted) <= set(dimensions):
        errors.append('input/options/dimension_ids: duplicate or unknown dimension')
    if source.get('schema_version') != '1.0' or not source.get('papers'):
        return errors + ['input: schema_version 1.0 and nonempty papers required']

    def key(p):
        return (p.get('paper_id'),p.get('document_version_id'))

    inputs = {}
    for p in source['papers']:
        k = key(p)
        if None in k or k in inputs:
            errors.append('input: missing or duplicate paper/version identity')
        inputs[k] = p
    output_keys = [key(p) for p in output['papers']]
    if len(set(output_keys)) != len(output_keys) or set(output_keys) != set(inputs):
        errors.append('output: paper/version identities must match input exactly')
    for p in output['papers']:
        tag = '/'.join(key(p))
        src = inputs.get(key(p))
        if src is None:
            continue
        def fail(message):
            errors.append(f'{tag}: {message}')
        units = {}
        for u in src.get('units',[]):
            uid = u.get('unit_id')
            if not uid or uid in units or u.get('source_type') not in SOURCE_KINDS or not isinstance(u.get('text'),str):
                fail('input unit has missing/duplicate ID, invalid source_type or non-text content')
                continue
            units[uid] = u
        if p['coverage'] != src.get('coverage'):
            fail('coverage must preserve the input scope')
        if not set(src.get('coverage_notes',[])) <= set(p['coverage_notes']):
            fail('coverage_notes must retain input limitations')
        if p['coverage'] != 'full_text' and p['processing_status'] != 'partial':
            fail('partial input cannot have complete processing_status')
        facts = {}
        fact_sources = {}
        for f in p['facts']:
            fid = f['fact_id']
            if fid in facts:
                fail(f'duplicate fact_id {fid}')
            facts[fid] = f
            fact_sources[fid] = set()
            for ev in f['evidence']:
                u = units.get(ev['unit_id'])
                if not u:
                    fail(f'{fid}: unknown unit_id {ev["unit_id"]}')
                    continue
                fact_sources[fid].add(u['source_type'])
                if ev['quote'] not in u['text']:
                    fail(f'{fid}: quote is not an exact source substring')
                if f['kind'] not in SOURCE_KINDS[u['source_type']]:
                    fail(f'{fid}: {f["kind"]} cannot be sourced from {u["source_type"]}')
        def check_refs(refs, where):
            if any(ref not in facts for ref in refs):
                fail(f'{where}: unknown fact reference')
            return set().union(*(fact_sources.get(ref,set()) for ref in refs))
        assessments = {}
        for a in p['assessments']:
            dim = a['dimension_id']
            if dim in assessments:
                fail(f'duplicate assessment {dim}')
            assessments[dim] = a
            refs = a['supporting_fact_ids'] + a['counter_fact_ids']
            for finding in a['findings']:
                refs += finding['fact_ids']
            sources = check_refs(refs, dim)
            fields = [x['field'] for x in a['findings']]
            if len(fields) != len(set(fields)) or set(fields) != set(dimensions[dim]['generated']):
                fail(f'{dim}: findings must contain exactly its defined generated fields')
            if a['grade'] is not None and not (a['supporting_fact_ids'] or a['counter_fact_ids']):
                fail(f'{dim}: non-null grade needs supporting or counter evidence')
            if a['status']=='insufficient' and not a['missing_evidence']:
                fail(f'{dim}: insufficient requires missing_evidence')
            if sources:
                if sources <= {'review','rebuttal'}:
                    allowed = {'review_consensus'}
                elif sources == {'structured'}:
                    allowed = {'upstream_summary'}
                elif sources <= DIRECT:
                    # Paper + prior work are both direct evidence and multiple sources.
                    # The contract permits either description; neither upgrades opinions.
                    allowed = {'paper_evidence','mixed_sources'} if len(sources)>1 else {'paper_evidence'}
                else:
                    allowed = {'mixed_sources'}
                if a['scope'] not in allowed:
                    fail(f'{dim}: scope must be one of {sorted(allowed)} for referenced sources')
            if a['status']=='supported' and not sources.intersection(DIRECT):
                fail(f'{dim}: opinions/upstream summaries cannot be independently supported')
        if set(assessments) != set(wanted):
            fail('assessments must contain exactly requested dimensions')
        issue_ids = set()
        for issue in p['issues']:
            if issue['issue_id'] in issue_ids:
                fail('duplicate issue_id')
            issue_ids.add(issue['issue_id'])
            if not set(issue['dimension_ids']) <= set(assessments):
                fail('issue references unassessed dimension')
            for fld in ['raised_fact_ids','response_fact_ids','followup_fact_ids']:
                check_refs(issue[fld], issue['issue_id'])
            response_kinds = {facts[x]['kind'] for x in issue['response_fact_ids'] if x in facts}
            followup_kinds = {facts[x]['kind'] for x in issue['followup_fact_ids'] if x in facts}
            if issue['response_fact_ids'] and response_kinds != {'author_response'}:
                fail('response_fact_ids must identify author responses')
            if issue['resolution']=='author_responded' and 'author_response' not in response_kinds:
                fail('author_responded requires a response')
            if issue['resolution']=='reviewer_acknowledged' and 'review_opinion' not in followup_kinds:
                fail('reviewer_acknowledged requires an explicit reviewer followup')
            if issue['resolution']=='independently_verified' and not followup_kinds.intersection({'execution_verification','resource_verification'}):
                fail('independently_verified requires a verification record')
        syn = p['synthesis']
        for refs in [syn['assessment_refs'],syn['breakthrough']['assessment_refs']]:
            if not set(refs) <= set(assessments):
                fail('synthesis references unassessed dimensions')
        strong = syn['breakthrough']['label']=='strong_candidate'
        priority = syn['reading_tier']=='priority_reading_candidate'
        if strong or priority:
            for dim in ['Q1','Q2','Q3','Q4']:
                a = assessments.get(dim,{})
                if a.get('status')!='supported' or a.get('grade') not in ['strong','moderate']:
                    fail(f'{dim}: high composite requires positive directly supported assessment')
            if not any('paper' in sources for sources in fact_sources.values()):
                fail('high composite requires paper facts')
        if strong:
            for dim in ['B1','B2','B3']:
                if assessments.get(dim,{}).get('status') not in ['supported','preliminary']:
                    fail(f'{dim}: breakthrough candidate needs assessment coverage')
            b1 = assessments.get('B1',{})
            refs = b1.get('supporting_fact_ids',[])+b1.get('counter_fact_ids',[])
            if not any('prior_work' in fact_sources.get(x,set()) for x in refs):
                fail('strong breakthrough requires actual prior-work evidence for B1')
        if priority and not any(assessments.get(d,{}).get('grade') in ['strong','moderate'] for d in ['B1','B2','B3','V1']):
            fail('priority reading requires positive value evidence')
    return errors

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path)
    p.add_argument('output',type=Path)
    a = p.parse_args()
    try:
        errors = validate(json.loads(a.input.read_text()),json.loads(a.output.read_text()))
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        print(json.dumps({'valid':False,'error':str(exc)},ensure_ascii=False))
        return 2
    print(json.dumps({'valid':not errors,'errors':errors,'scope':'schema, references, exact quotes, provenance and state invariants; not semantic or scientific verification'},ensure_ascii=False,indent=2))
    return 1 if errors else 0

if __name__ == '__main__':
    sys.exit(main())
