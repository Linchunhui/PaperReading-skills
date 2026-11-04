"""Validate schemas, source spans, source roles and reference dependencies.

This does not establish semantic entailment, novelty or scientific correctness.
"""
from pathlib import Path
import argparse,json

FIELDS=['background','direction','problem','approach','methods','summary','results','reported_limitations']
DIMS=['B1','B2','B3','V1','Q1','Q2','Q3','Q4','Q5','Q6']

def validator_class():
    try:
        from jsonschema import Draft202012Validator
    except ModuleNotFoundError:
        # A local install can keep dependencies private to this Skill instead
        # of modifying the caller's global Python environment.
        import sys
        deps=Path(__file__).resolve().parents[1]/'.deps'
        if not deps.is_dir():
            raise SystemExit('Missing jsonschema. Install scripts/requirements.txt in this Python environment, or into '+str(deps)+' with pip --target.')
        sys.path.insert(0,str(deps))
        from jsonschema import Draft202012Validator
    return Draft202012Validator

def validate(inp,out):
    schema_name='workflow-output.schema.json' if out.get('schema_version')=='2.0' else 'output.schema.json'
    schema=json.loads((Path(__file__).resolve().parents[1]/'references'/schema_name).read_text())
    errs=[f'{"/".join(map(str,e.absolute_path))}: {e.message}' for e in validator_class()(schema).iter_errors(out)]
    if errs:return errs
    source={(p['paper_id'],p['document_version_id']):p for p in inp['papers']}
    if len(source)!=len(inp['papers']):return ['Duplicate input paper/version identity']
    def unique(rows,key,label):
        ids=[r[key] for r in rows]
        if len(ids)!=len(set(ids)):errs.append(label+': duplicate '+key)
        return {r[key]:r for r in rows}
    out_keys={(p['paper_id'],p['document_version_id']) for p in out['papers']}
    if len(out_keys)!=len(out['papers']) or out_keys!=set(source):errs.append('Input/output paper versions must match exactly')
    for p in out['papers']:
        key=(p['paper_id'],p['document_version_id'])
        if key not in source:continue
        original=source[key];units={u['unit_id']:u for u in original['units']}
        if len(units)!=len(original['units']):errs.append('Duplicate input units')
        if p['coverage']!=original['coverage']:errs.append('Coverage changed')
        if p['coverage']!='full_text' and p['processing_status']!='partial':errs.append('Non-full input requires partial processing status')
        ev=unique(p['evidence'],'evidence_id','evidence');facts=unique(p['facts'],'fact_id','facts')
        for e in ev.values():
            if e['unit_id'] not in units or e['quote'] not in units[e['unit_id']]['text']:errs.append('Evidence substring mismatch: '+e['evidence_id'])
        allowed={'prior_work':'prior_work','review_opinion':'review','author_response':'rebuttal','resource_check':'resource_check','execution_check':'execution_check','upstream_summary':'structured'}
        for f in facts.values():
            if not set(f['evidence_ids'])<=set(ev):errs.append('Unknown evidence on fact: '+f['fact_id']);continue
            # An explicit upstream origin cannot be overridden by a more
            # prestigious source_type. This is a provenance invariant.
            types={('structured' if units[ev[eid]['unit_id']].get('origin')=='structured' else units[ev[eid]['unit_id']].get('source_type','paper')) for eid in f['evidence_ids'] if ev[eid]['unit_id'] in units}
            if f['kind'] in allowed and allowed[f['kind']] not in types:errs.append('Fact source role mismatch: '+f['fact_id'])
            if types and types=={'structured'} and f['kind']!='upstream_summary':errs.append('Structured material promoted to paper fact: '+f['fact_id'])
            if f['kind'] in {'metadata','contribution','method','reported_result','theorem','limitation','resource_statement'} and 'paper' not in types:
                errs.append('Non-paper source promoted to paper fact: '+f['fact_id'])
            if f['kind']=='reported_result' and f['observation'] is None:errs.append('Reported result missing measurement: '+f['fact_id'])
        def check_fact_refs(node,label=''):
            if isinstance(node,dict):
                for field in ['fact_ids','supporting_fact_ids','counter_fact_ids']:
                    if field in node and not set(node[field])<=set(facts):errs.append('Unknown fact dependency '+label+'/'+field)
                for k,v in node.items():check_fact_refs(v,label+'/'+k)
            elif isinstance(node,list):
                for i,v in enumerate(node):check_fact_refs(v,label+'/'+str(i))
        check_fact_refs(p)
        data=p['understanding'];items=unique([i for f in FIELDS for i in data[f]],'item_id','understanding')
        unique(data['problem_signatures'],'signature_id','problem_signatures')
        problems={i['item_id'] for i in data['problem']}
        for sig in data['problem_signatures']:
            if not set(sig['problem_item_ids'])<=problems:errs.append('Unknown problem reference in signature')
        assessments=unique(p['assessments'],'dimension_id','assessments')
        requested=inp.get('options',{}).get('dimension_ids')
        expected=set(DIMS if requested is None else requested)
        if set(assessments)!=expected:errs.append('Requested dimensions not accounted for')
        for a in assessments.values():
            if a['status'] in {'insufficient','not_applicable'}:
                if a['grade'] is not None:errs.append('Insufficient/not-applicable grade must be null')
            elif a['grade'] is None or not a['supporting_fact_ids']:errs.append('Judgment grade/support missing: '+a['dimension_id'])
        reasons=unique(p['recommendations'],'reason_id','recommendations')
        for r in reasons.values():
            if not set(r['assessment_refs'])<=set(assessments):errs.append('Unknown reason assessment')
            if r['angle']=='breakthrough':
                needed={'B1','B2','B3','Q1','Q2','Q3','Q4'}
                if not all(d in assessments and assessments[d]['status']=='supported' for d in needed):errs.append('Breakthrough gate missing supported dimensions')
                if not any(f['kind']=='prior_work' for f in facts.values()):errs.append('Breakthrough lacks independently supplied prior work')
        unique(p['reuse_cards'],'reuse_id','reuse');unique(p['insight_rules'],'rule_id','rules');unique(p['glossary'],'term_id','glossary')
        for card in p['reuse_cards']:
            if card['verification_status']=='verified' and not any(facts[f]['kind']=='execution_check' for f in card['fact_ids'] if f in facts):errs.append('Verified reuse lacks actual execution evidence')
        for resource in p['metadata']['resources']:
            if resource['status'] in {'access_checked','executed'}:
                required='resource_check' if resource['status']=='access_checked' else 'execution_check'
                if not any(facts[f]['kind']==required for f in resource['fact_ids'] if f in facts):errs.append('Resource verification status lacks matching evidence')
        aff=unique(p['metadata']['affiliations'],'affiliation_id','affiliations')
        unique(p['metadata']['authors'],'author_id','authors')
        for author in p['metadata']['authors']:
            if not set(author['affiliation_ids'])<=set(aff):errs.append('Unknown author affiliation')
        display=p['display']
        if not set(display['highlight_item_ids'])<=set(items):errs.append('Unknown display item')
        if not set(display['recommendation_ids'])<=set(reasons):errs.append('Unknown display reason')
        if len(display['recommendation_ids'])!=len(set(display['recommendation_ids'])):errs.append('Duplicate displayed reason')
    if out.get('schema_version')=='2.0' and not errs:
        from validate_workflow import validate_workflow
        errs.extend(validate_workflow(inp,out))
    return errs

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');ap.add_argument('--report');a=ap.parse_args()
    errors=validate(json.loads(Path(a.input).read_text()),json.loads(Path(a.output).read_text()))
    result={'ok':not errors,'errors':errors,'scope':'schema, identities, roles and source-span/dependency checks; not semantic correctness'}
    if a.report:Path(a.report).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False));raise SystemExit(bool(errors))
