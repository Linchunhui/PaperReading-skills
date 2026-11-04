#!/usr/bin/env python3
"""Validate local skill contracts and source references; not scientific accuracy."""
import argparse
import json
from pathlib import Path
from urllib.parse import unquote, urlparse


def validate(input_data, output_data, schema_dir):
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    from referencing.exceptions import NoSuchResource
    schema_dir = Path(schema_dir).resolve()
    def retrieve(uri):
        parsed = urlparse(uri)
        path = Path(unquote(parsed.path)).resolve()
        if parsed.scheme != 'file' or schema_dir not in path.parents:
            raise NoSuchResource(ref=uri)
        return Resource.from_contents(json.loads(path.read_text(encoding='utf-8')))
    registry = Registry(retrieve=retrieve)
    errors = []
    for filename, data in [('input.schema.json', input_data), ('output.schema.json', output_data)]:
        path = schema_dir / filename
        schema = json.loads(path.read_text(encoding='utf-8'))
        Draft202012Validator.check_schema(schema)
        schema.setdefault('$id', path.as_uri())
        for error in Draft202012Validator(schema, registry=registry).iter_errors(data):
            loc = '/'.join(map(str,error.absolute_path)) or '$'
            errors.append(f'{filename}:{loc}: {error.message}')
    if errors:
        return errors
    papers, units, assets = {}, {}, {}
    for paper in input_data['papers']:
        key = (paper['paper_id'], paper['document_version_id'])
        if key in papers:
            errors.append(f'duplicate input paper/version: {key}')
        papers[key] = paper
        for unit in paper['units']:
            unit_key = (*key, unit['unit_id'])
            if unit_key in units:
                errors.append(f'duplicate input unit: {unit_key}')
            units[unit_key] = unit['text']
        asset_ids = [a['asset_id'] for a in paper['assets']]
        if len(asset_ids) != len(set(asset_ids)):
            errors.append(f'duplicate input asset IDs: {key}')
        assets[key] = set(asset_ids)
        for asset in paper['assets']:
            for uid in asset['source_unit_ids']:
                if (*key,uid) not in units:
                    errors.append(f'unknown source unit for asset {asset["asset_id"]}: {uid}')

    def walk(node, path='$', paper_key=None):
        if isinstance(node, dict):
            if 'paper_id' in node and 'document_version_id' in node:
                paper_key = (node['paper_id'],node['document_version_id'])
                if paper_key not in papers:
                    errors.append(f'{path}: unknown paper/version {paper_key}')
            if all(k in node for k in ('paper_id','document_version_id','unit_id','quote')):
                key = (node['paper_id'],node['document_version_id'],node['unit_id'])
                if key not in units:
                    errors.append(f'{path}: unknown evidence unit {key}')
                elif not node['quote'] or node['quote'] not in units[key]:
                    errors.append(f'{path}: evidence quote is not an exact nonempty source substring')
            if 'asset_ids' in node and isinstance(node['asset_ids'],list):
                for asset_id in node['asset_ids']:
                    if asset_id not in assets.get(paper_key,set()):
                        errors.append(f'{path}: unknown supplied asset {asset_id}')
            for k,v in node.items():
                walk(v,f'{path}/{k}',paper_key)
        elif isinstance(node,list):
            for i,v in enumerate(node): walk(v,f'{path}/{i}',paper_key)
    walk(output_data)
    if 'papers' in output_data:
        out_keys = [(p['paper_id'],p['document_version_id']) for p in output_data['papers']]
        if len(out_keys) != len(set(out_keys)):
            errors.append('duplicate output paper/version')
        if set(out_keys) != set(papers):
            errors.append('output papers must account for every input paper/version exactly once')
        for p in output_data['papers']:
            key = (p['paper_id'],p['document_version_id'])
            if key in papers and p.get('coverage') != papers[key]['coverage']:
                errors.append(f'output coverage changed for {key}')
            if p.get('coverage') != 'full_text' and p.get('status') == 'complete':
                errors.append(f'{key}: incomplete/structured-only coverage requires partial status')
    def unique(items, field, label):
        values = [x[field] for x in items]
        if len(values) != len(set(values)):
            errors.append(f'{label}: duplicate {field}')
        return set(values)

    skill = output_data.get('skill')
    options = input_data.get('options', {})
    if skill == 'paper-metadata':
        for paper in output_data['papers']:
            data = paper['data']; extracted = data['extracted']
            unique(extracted['authors'],'author_id','authors')
            aff = unique(extracted['affiliations'],'affiliation_id','affiliations')
            refs = unique(extracted['references'],'reference_id','references')
            unique(extracted['benchmark_observations'],'observation_id','benchmark observations')
            for author in extracted['authors']:
                if not set(author['affiliation_ids']) <= aff:
                    errors.append('author references an unknown affiliation_id')
            for work in data['generated']['related_work']:
                if not set(work['work_reference_ids']) <= refs:
                    errors.append('related_work references an unknown reference_id')
    elif skill == 'paper-structured-summary':
        for paper in output_data['papers']:
            data = paper['data']
            items = [item for field in ['background','direction','problem','approach','methods','summary','results','reported_limitations'] for item in data[field]]
            unique(items,'item_id','structured items')
            problems = {item['item_id'] for item in data['problem']}
            unique(data['problem_signatures'],'signature_id','problem signatures')
            for sig in data['problem_signatures']:
                if not set(sig['problem_item_ids']) <= problems:
                    errors.append('problem signature references an unknown problem item')
    elif skill == 'paper-brief':
        priorities = options.get('priority_institutions',[])
        priority_ids = {x['priority_id'] for x in priorities if isinstance(x,dict) and 'priority_id' in x}
        selected = options.get('deliverables',['abstract','deep_read','home_digest','recommendations'])
        for paper in output_data['papers']:
            data = paper['data']
            unique(data['recommendations'],'reason_id','recommendations')
            if data['deep_read']:
                unique(data['deep_read']['sections'],'section_id','deep read sections')
            for field in ['abstract','deep_read','home_digest','recommendations']:
                if field not in selected and data[field] not in (None,[]):
                    errors.append(f'{field}: emitted an unrequested deliverable')
                if data[field] in (None,[]) and not any(x['field'] == field or x['field'] == f'/data/{field}' for x in data['omitted']):
                    errors.append(f'{field}: missing explanation for omitted deliverable')
            for reason in data['recommendations']:
                match = reason['institution_match']
                if match and match['priority_id'] not in priority_ids:
                    errors.append('institution recommendation references an unconfigured priority_id')
    elif skill == 'paper-directions':
        taxonomy = options.get('taxonomy') or {}
        categories_list = taxonomy.get('categories',[])
        categories = {c['category_id']:c for c in categories_list if isinstance(c,dict) and 'category_id' in c}
        if len(categories) != len(categories_list): errors.append('taxonomy has duplicate/missing category IDs')
        if output_data['taxonomy_version'] != taxonomy.get('version'):
            errors.append('output taxonomy_version differs from supplied taxonomy version')
        proposals = {}
        mode = options.get('mode','all')
        for paper in output_data['papers']:
            data = paper['data']
            unique(data['assignments'],'category_id','assignments')
            unique(data['proposed_directions'],'proposed_id','proposed directions')
            if mode not in ('all','extract') and data['extracted_directions']: errors.append('extracted directions emitted in disabled mode')
            if mode not in ('all','classify') and data['assignments']: errors.append('assignments emitted in disabled mode')
            if (mode not in ('all','propose') or not options.get('allow_new_directions',True)) and data['proposed_directions']:
                errors.append('new directions emitted when proposals are disabled')
            counts={}
            for assignment in data['assignments']:
                category = categories.get(assignment['category_id'])
                if not category or not category.get('definition') or not taxonomy.get('version'):
                    errors.append('assignment references unknown or undefined taxonomy category')
                elif assignment['axis'] != category.get('axis'):
                    errors.append('assignment axis differs from taxonomy category')
            for proposal in data['proposed_directions']:
                if not set(proposal['parent_ids'] + proposal['nearest_category_ids']) <= set(categories):
                    errors.append('proposed direction references an unknown category')
                definition={k:proposal[k] for k in ['label','axis','definition','inclusion_criteria','exclusion_criteria','parent_ids']}
                pid=proposal['proposed_id']
                if pid in proposals and proposals[pid] != definition:
                    errors.append('same proposed_id reused with inconsistent definition')
                proposals[pid]=definition
            for item in data['assignments']+data['proposed_directions']:
                counts[item['axis']] = counts.get(item['axis'],0)+1
            limit=options.get('max_labels_per_axis',3)
            if not isinstance(limit,int) or isinstance(limit,bool) or limit<1:
                errors.append('max_labels_per_axis must be a positive integer')
            elif any(n>limit for n in counts.values()): errors.append('max_labels_per_axis exceeded')
    elif skill == 'paper-cluster-synthesis':
        def identity(x): return (x['paper_id'],x['document_version_id'])
        cluster_ids = unique(output_data['clusters'],'cluster_id','clusters')
        memberships={}
        for cluster in output_data['clusters']:
            keys=[identity(x) for x in cluster['members']]
            if len(keys)!=len(set(keys)): errors.append('duplicate member within a cluster')
            if cluster['kind']=='problem_cluster' and len({k[0] for k in keys})<2:
                errors.append('problem cluster requires at least two distinct paper IDs')
            for m in cluster['members']:
                memberships.setdefault(identity(m),[]).append(m)
                if not any(identity(ev)==identity(m) for ev in m['evidence']):
                    errors.append('cluster member has no evidence from that paper/version')
            for comparison in cluster['result_comparisons']:
                if not {identity(x) for x in comparison['papers']} <= set(keys):
                    errors.append('result comparison references a paper outside its cluster')
        unassigned=output_data['unassigned']
        unassigned_keys=[identity(x) for x in unassigned]
        if len(unassigned_keys)!=len(set(unassigned_keys)): errors.append('duplicate unassigned paper/version')
        if set(memberships)&set(unassigned_keys): errors.append('paper/version both assigned and unassigned')
        if set(memberships)|set(unassigned_keys) != set(papers): errors.append('cluster output must account for every input paper/version')
        by_paper={}
        for key,members in memberships.items():
            by_paper.setdefault(key[0],set()).add(key[1])
            if len(members)>1:
                if not options.get('allow_overlap',True): errors.append('overlap emitted while allow_overlap is false')
                if any(m['membership_type']!='multiple_problem_view' for m in members): errors.append('overlap requires multiple_problem_view')
                if len({m['problem_focus'] for m in members})!=len(members): errors.append('overlap requires distinct problem_focus descriptions')
        if any(len(versions)>1 for versions in by_paper.values()): errors.append('multiple versions of the same paper counted as members')
        retained = set(memberships) | {identity(x) for x in unassigned if x['reason_code'] != 'duplicate_version'}
        for item in unassigned:
            duplicate=item['duplicate_of']
            if item['reason_code']=='duplicate_version':
                if not duplicate or identity(duplicate) not in retained or identity(duplicate)==identity(item):
                    errors.append('duplicate version must point to a retained nonduplicate record')
            elif duplicate is not None: errors.append('duplicate_of only allowed for duplicate_version')
        candidates=options.get('candidate_clusters',[])
        candidate_ids={x['candidate_cluster_id'] for x in candidates}
        review_ids=[x['candidate_cluster_id'] for x in output_data['candidate_review']]
        if set(review_ids)!=candidate_ids or len(review_ids)!=len(set(review_ids)):
            errors.append('candidate_review must cover each supplied candidate exactly once')
        for review in output_data['candidate_review']:
            if not set(review['result_cluster_ids']) <= cluster_ids: errors.append('candidate review references unknown result cluster')
    return errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--schema-dir', type=Path, default=Path(__file__).resolve().parent.parent/'schemas')
    args = p.parse_args()
    try:
        errors = validate(json.loads(args.input.read_text(encoding='utf-8')),json.loads(args.output.read_text(encoding='utf-8')),args.schema_dir)
    except ImportError:
        raise SystemExit('Missing jsonschema; install scripts/requirements.txt in your chosen environment.')
    except Exception as e:
        raise SystemExit(f'Validation could not complete: {e}')
    print(json.dumps({'valid':not errors,'errors':errors,'scope':'schema, identity, coverage, exact evidence, assets and selected cross-field links; not scientific accuracy'},ensure_ascii=False,indent=2))
    return 1 if errors else 0

if __name__ == '__main__':
    raise SystemExit(main())
