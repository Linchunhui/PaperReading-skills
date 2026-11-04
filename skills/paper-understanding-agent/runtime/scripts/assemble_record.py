"""Assemble independently generated stage files. This script makes no model calls."""
import argparse
import hashlib
import json
from pathlib import Path
from validate_output import validate, validator_class
from validate_workflow import input_digest, SINGLES

ROOT = Path(__file__).resolve().parents[1]

def load(path):
    return json.loads(Path(path).read_text())

def assemble(inp, manifest, directory):
    if len(inp['papers']) != 1:
        raise ValueError('One paper is required per workflow manifest')
    source = inp['papers'][0]
    identity = (source['paper_id'], source['document_version_id'])
    digest = input_digest(inp)
    if (manifest['paper_id'], manifest['document_version_id']) != identity or manifest['input_sha256'] != digest:
        raise ValueError('Manifest paper/version/input hash mismatch')
    schema = load(ROOT / 'references/workflow-output.schema.json')
    cls = validator_class()
    stage_validator = cls({'$defs': schema['$defs'], '$ref': '#/$defs/stage_artifact'})
    scope_errors = list(cls({'$defs': schema['$defs'], '$ref': '#/$defs/scope'}).iter_errors(manifest['scope']))
    if scope_errors:
        raise ValueError('Invalid scope: ' + '; '.join(e.message for e in scope_errors))
    stages = []; traces = []; ids = set()
    for entry in manifest['stages']:
        path = Path(directory) / entry['path']
        raw = path.read_bytes()
        stage = json.loads(raw)
        problems = list(stage_validator.iter_errors(stage))
        if problems:
            raise ValueError('Invalid stage ' + entry['path'] + ': ' + '; '.join(e.message for e in problems))
        if (stage['stage_id'], stage['kind']) != (entry['stage_id'], entry['kind']) or stage['stage_id'] in ids:
            raise ValueError('Stage manifest mismatch or duplicate: ' + entry['stage_id'])
        if (stage['paper_id'], stage['document_version_id']) != identity or stage['input_sha256'] != digest:
            raise ValueError('Stage paper/version/input hash mismatch: ' + stage['stage_id'])
        ids.add(stage['stage_id']); stages.append(stage)
        traces.append({k: stage[k] for k in ['stage_id', 'kind', 'paper_id', 'document_version_id', 'input_sha256',
                                            'status', 'producer', 'source_unit_ids', 'context_unit_ids']})
        traces[-1].update({'artifact': entry['path'], 'artifact_sha256': hashlib.sha256(raw).hexdigest(),
                           'fact_ids': [f['fact_id'] for f in stage['facts']],
                           'evidence_ids': [e['evidence_id'] for e in stage['evidence']]})
    singles = {}
    for kind in SINGLES:
        matches = [s for s in stages if s['kind'] == kind]
        if len(matches) != 1:
            raise ValueError('Required singleton stage missing or repeated: ' + kind)
        singles[kind] = matches[0]['data']
    if singles['metadata']['metadata']['references']:
        raise ValueError('Metadata stage must leave references empty; references has a separate owner')
    p = {k: source[k] for k in ['paper_id', 'document_version_id', 'coverage']}
    partial = source['coverage'] != 'full_text' or manifest['scope']['unresolved_units'] or any(s['status'] == 'partial' for s in stages)
    p.update({'profile': 'comprehensive', 'processing_status': 'partial' if partial else 'complete'})
    for kind in ['metadata', 'understanding', 'assessment', 'reading']:
        p.update(singles[kind])
    p['metadata']['references'] = singles['references']['references']
    p['bibliography'] = {k: singles['references'][k] for k in ['unparsed_segments', 'excluded_segments']}
    for field, key in [('evidence', 'evidence_id'), ('facts', 'fact_id')]:
        merged = {}
        for stage in stages:
            local_ids = set()
            for row in stage[field]:
                rid = row[key]
                if rid in local_ids:
                    raise ValueError('Duplicate ' + key + ' within stage: ' + rid)
                local_ids.add(rid)
                if rid in merged and merged[rid] != row:
                    raise ValueError('Conflicting ' + key + ': ' + rid)
                merged[rid] = row
        p[field] = list(merged.values())
    for field in ['missing_information', 'limitations']:
        p[field] = []
        for stage in stages:
            for item in stage[field]:
                if item not in p[field]:
                    p[field].append(item)
    for kind, field, id_key, group_key in [('page', 'page_extractions', 'page_id', 'pages'),
                                          ('section', 'section_summaries', 'section_id', 'sections')]:
        rows = [dict(s['data'], source_unit_ids=s['source_unit_ids']) for s in stages if s['kind'] == kind]
        order = {g[id_key]: i for i, g in enumerate(manifest['scope'][group_key])}
        p[field] = sorted(rows, key=lambda row: order.get(row[id_key], len(order)))
    p['workflow'] = {'input_sha256': digest, 'scope': manifest['scope'], 'stages': traces}
    out = {'schema_version': '2.0', 'skill': 'paper-understanding', 'papers': [p]}
    errors = validate(inp, out)
    if errors:
        raise ValueError('Workflow validation failed:\n' + '\n'.join(errors))
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input'); ap.add_argument('manifest', nargs='?'); ap.add_argument('output', nargs='?')
    ap.add_argument('--input-hash', action='store_true'); ap.add_argument('--report')
    args = ap.parse_args()
    if not args.input_hash and (not args.manifest or not args.output):
        ap.error('manifest and output are required unless --input-hash is used')
    output_path = Path(args.output).resolve() if args.output else None
    input_paths = {Path(args.input).resolve()}
    if args.manifest:
        input_paths.add(Path(args.manifest).resolve())
    if output_path in input_paths or (args.report and Path(args.report).resolve() in input_paths | {output_path}):
        ap.error('Output/report cannot overwrite input, manifest or each other')
    result = {'ok': False, 'scope': 'schema, stage coverage, source spans and dependencies; not semantic correctness'}
    try:
        inp = load(args.input)
        if args.input_hash:
            print(input_digest(inp)); return 0
        manifest_path = Path(args.manifest)
        manifest = load(manifest_path)
        stage_paths = {(manifest_path.parent / s['path']).resolve() for s in manifest['stages']}
        if output_path in stage_paths or (args.report and Path(args.report).resolve() in stage_paths):
            raise ValueError('Output/report cannot overwrite stage artifacts')
        out = assemble(inp, manifest, manifest_path.parent)
        # Validation failure never overwrites an existing successful record.
        text = json.dumps(out, ensure_ascii=False, indent=2) + '\n'
        output_path.write_text(text)
        result.update(ok=True, errors=[], paper_id=inp['papers'][0]['paper_id'])
    except (ValueError, KeyError, TypeError, OSError) as exc:
        result['errors'] = [str(exc)]
    if args.report:
        Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['ok'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
