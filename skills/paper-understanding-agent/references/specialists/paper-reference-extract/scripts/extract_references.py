#!/usr/bin/env python3
"""One PP bibliography -> one vLLM structured completion; preserve source coverage."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone

SKILL = Path(__file__).resolve().parents[1]
VERSION = 'paper-reference-extract-v1.4'


def packed(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(obj):
    return hashlib.sha256(packed(obj).encode()).hexdigest()


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def read(path):
    return json.loads(Path(path).read_text())


def generation_contract(validation_schema):
    """xgrammar regex strings reject escaped quotes; retain full checks after decoding."""
    schema = copy.deepcopy(validation_schema)
    def visit(node):
        if isinstance(node, dict):
            if node.get('type') == 'string' and node.get('pattern', '').startswith('^[^'):
                for key in ['pattern', 'minLength', 'maxLength']:
                    node.pop(key, None)
            for value in node.values(): visit(value)
        elif isinstance(node, list):
            for value in node: visit(value)
    visit(schema)
    return schema


def prepare(pp_dir):
    pp_dir = Path(pp_dir).resolve()
    manifest = read(pp_dir / 'manifest.json')
    if manifest.get('status') != 'complete':
        raise ValueError('PP parsing is incomplete; do not use partial bibliography')
    blocks, pages = [], []
    seen_pages = set()
    for row in sorted(manifest['pages'], key=lambda x: int(x['page'])):
        number = int(row['page'])
        if number in seen_pages:
            raise ValueError(f'Duplicate manifest page {number}')
        seen_pages.add(number)
        # Resolve the frozen page basename locally so a copied pp_dir stays portable.
        path = pp_dir / Path(row['json']).name
        raw = path.read_bytes()
        data = json.loads(raw)
        body = data.get('res', data)
        native = body.get('parsing_res_list')
        if not isinstance(native, list):
            raise ValueError(f'Missing parsing_res_list: {path}')
        expected_pdf = manifest.get('pdf_sha256')
        actual_pdf = data.get('_paperreader', {}).get('pdf_sha256')
        if expected_pdf and actual_pdf and expected_pdf != actual_pdf:
            raise ValueError(f'PP page belongs to a different PDF: {path}')
        pages.append({'page': number, 'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()})
        ordered = sorted(enumerate(native), key=lambda x: (x[1].get('block_order') if isinstance(x[1].get('block_order'), (int, float)) else x[0], x[0]))
        for index, block in ordered:
            if block.get('block_label') != 'reference_content':
                continue
            text = block.get('block_content')
            if not isinstance(text, str):
                raise ValueError(f'Non-text reference_content: {path} block {index}')
            if not text.strip():
                continue
            blocks.append({'id': f'p{number:04d}-b{index:04d}', 'text': text,
                           'locator': {'page': number, 'json_path': str(path),
                                       'json_pointer': ('/res' if 'res' in data else '') + f'/parsing_res_list/{index}',
                                       'block_id': block.get('block_id'), 'block_order': block.get('block_order'),
                                       'bbox': block.get('block_bbox')}})
    expected_count = manifest.get('page_count')
    if expected_count and seen_pages != set(range(1, expected_count + 1)):
        raise ValueError('PP manifest page_count mismatch')
    source = {'paper_id': manifest['paper_id'], 'scope': 'pp_json.reference_content',
              'pdf_sha256': manifest.get('pdf_sha256'), 'parser_model': manifest.get('model'),
              'reference_blocks': blocks, 'page_files': pages}
    source['source_sha256'] = digest(source)
    return source


def canonical(text):
    """OCR typography/whitespace only; retains a mapping into the untouched source."""
    chars, positions = [], []
    for offset, char in enumerate(text):
        for item in unicodedata.normalize('NFKD', char).casefold():
            if item.isalnum():
                chars.append(item)
                positions.append(offset)
    return ''.join(chars), positions


def materialize(generated, source):
    by_id = {b['id']: b for b in source['reference_blocks']}
    order = {b['id']: n for n, b in enumerate(source['reference_blocks'])}
    covered = {bid: set() for bid in by_id}
    errors, references, unparsed = [], [], []
    previous = (-1, -1)

    def locate(item, context, is_reference):
        ids = item['source_block_ids']
        if len(set(ids)) != len(ids) or any(bid not in by_id for bid in ids):
            errors.append(context + ': invalid or duplicate source_block_ids')
            return [], ''
        if ids != sorted(ids, key=order.get):
            errors.append(context + ': source blocks out of reading order')
        # A reference cannot skip other reference blocks in the input.
        if ids and [order[x] for x in ids] != list(range(order[ids[0]], order[ids[-1]] + 1)):
            errors.append(context + ': skipped intervening source blocks')
        joined, offsets = '', []
        for bid in ids:
            offsets.append((bid, len(joined), len(joined) + len(by_id[bid]['text'])))
            joined += by_id[bid]['text'] + '\n'
        needle, _ = canonical(item['raw_text'])
        haystack, mapping = canonical(joined)
        start = haystack.find(needle) if needle else -1
        if start < 0:
            errors.append(context + ': raw_text is not a contiguous copy of the supplied blocks')
            return [], joined
        # Locate repeated identical citations by the first not-yet-covered occurrence.
        while start >= 0:
            lower, upper = mapping[start], mapping[start + len(needle) - 1] + 1
            candidates = []
            overlap = False
            for bid, a, z in offsets:
                lo, hi = max(lower, a) - a, min(upper, z) - a
                if hi <= lo:
                    continue
                norm, pos = canonical(by_id[bid]['text'])
                matched = {k for k, v in enumerate(pos) if lo <= v < hi}
                if matched & covered[bid]:
                    overlap = True
                candidates.append((bid, lo, hi, matched))
            if not overlap:
                break
            start = haystack.find(needle, start + 1)
        if start < 0:
            errors.append(context + ': citation duplicates/overlaps previously consumed text')
            return [], joined
        locators = []
        for bid, lo, hi, matched in candidates:
            covered[bid].update(matched)
            locators.append({'source_block_id': bid, **by_id[bid]['locator'],
                             'character_start': lo, 'character_end': hi,
                             'quote': by_id[bid]['text'][lo:hi]})
        if set(ids) != {x['source_block_id'] for x in locators}:
            errors.append(context + ': declared block contributes no citation text')
        return locators, item['raw_text']

    for index, item in enumerate(generated['references'], 1):
        context = f'reference {index}'
        locators, raw = locate(item, context, True)
        if locators:
            current = (order[locators[0]['source_block_id']], locators[0]['character_start'])
            if current < previous:
                errors.append(context + ': references are not in source order')
            previous = current
        literal, _ = canonical(raw)
        fields = {'title': item['title'], **{f'author[{n}]': a for n, a in enumerate(item['authors'])}, **item['source']}
        fields.pop('type', None)
        if item['label']:
            fields['label'] = item['label']
        for key, value in fields.items():
            if value:
                norm, _ = canonical(value)
                if not norm or norm not in literal:
                    errors.append(f'{context}: {key} absent from cited text: {value}')
        references.append({'reference_id': f'ref-{index:04d}', **item, 'locators': locators})
    for index, item in enumerate(generated['unparsed_segments'], 1):
        locators, _ = locate(item, f'unparsed segment {index}', False)
        unparsed.append({**item, 'locators': locators})
    gaps = []
    for bid, block in by_id.items():
        norm, positions = canonical(block['text'])
        missing = [i for i in range(len(norm)) if i not in covered[bid]]
        if missing:
            gaps.append({'source_block_id': bid, 'uncovered_characters': len(missing),
                         'preview': block['text'][positions[missing[0]]:positions[missing[-1]] + 1][:240]})
    if gaps:
        errors.append(f'{len(gaps)} reference blocks have uncovered source text')
    labels = [re.match(r'^\s*\[(\d+)\]', b['text']) for b in source['reference_blocks']]
    numbered = bool(labels) and all(labels) and [int(m[1]) for m in labels] == list(range(1, len(labels) + 1))
    numbered = numbered and all(len(re.findall(r'(?m)^\s*\[\d+\]', b['text'])) == 1 for b in source['reference_blocks'])
    if numbered:
        expected = {b['id']: '[' + m[1] + ']' for b, m in zip(source['reference_blocks'], labels)}
        for index, item in enumerate(references, 1):
            ids = item['source_block_ids']
            if len(ids) != 1 or item['label'] != expected.get(ids[0]):
                errors.append(f'reference {index}: numbered citation split or label/source mismatch')
        if not unparsed and len(references) != len(labels):
            errors.append('Numbered bibliography entry count differs from explicit source labels')
    coverage = {'source_blocks': len(by_id), 'references': len(references),
                'unparsed_segments': len(unparsed), 'uncovered_blocks': gaps,
                'source_text_covered': not gaps, 'bibliography_fully_parsed': not gaps and not unparsed,
                'explicit_numbered_entries': len(labels) if numbered else None,
                'unparsed_handling': 'Explicitly retained; not silently treated as extracted references.'}
    return references, unparsed, coverage, errors


def call_api(args, payload, dest):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(args.base_url.rstrip('/') + '/chat/completions',
                                 data=packed(payload).encode(), headers={'Content-Type': 'application/json'})
    content, reasoning, usage, finish, model = [], [], {}, None, None
    inside_string, escaped, whitespace_run = False, False, 0
    started = time.monotonic()
    try:
        response = opener.open(req, timeout=args.timeout)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors='replace')
        save(dest / 'http-error.json', {'status': exc.code, 'body': body})
        raise ValueError(f'vLLM HTTP {exc.code}: {body}') from exc
    with response, (dest / 'stream.jsonl').open('w') as log:
        for line in response:
            if not line.startswith(b'data:'):
                continue
            line = line[5:].strip()
            if line == b'[DONE]':
                break
            event = json.loads(line)
            log.write(packed({'elapsed_s': time.monotonic() - started, 'event': event}) + '\n')
            log.flush()
            if event.get('error'):
                raise RuntimeError(packed(event['error']))
            model = event.get('model', model)
            usage = event.get('usage') or usage
            for choice in event.get('choices', []):
                delta = choice.get('delta', {})
                piece = delta.get('content') or ''
                content.append(piece)
                for char in piece:
                    if inside_string:
                        whitespace_run = 0
                        if escaped:
                            escaped = False
                        elif char == '\\':
                            escaped = True
                        elif char == '"':
                            inside_string = False
                    elif char == '"':
                        inside_string, whitespace_run = True, 0
                    elif char.isspace():
                        whitespace_run += 1
                    else:
                        whitespace_run = 0
                    if whitespace_run > 512:
                        (dest / 'partial-content.txt').write_text(''.join(content))
                        raise ValueError('Degenerate JSON whitespace loop; complete input and partial response retained')
                reasoning.append(delta.get('reasoning') or delta.get('reasoning_content') or '')
                finish = choice.get('finish_reason') or finish
    result = {'model': model, 'content': ''.join(content), 'reasoning': ''.join(reasoning),
              'finish_reason': finish, 'usage': usage, 'elapsed_s': time.monotonic() - started}
    save(dest / 'response.json', result)
    (dest / 'content.txt').write_text(result['content'])
    if model != args.model or finish != 'stop':
        raise ValueError(f'Unexpected model/finish: {model} / {finish}')
    return result


def run(args):
    source = prepare(args.pp_dir)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    schema = read(SKILL / 'references/schema.json')
    transport_schema = generation_contract(schema)
    skill = (SKILL / 'PROFILE.md').read_text().split('---', 2)[2].strip()
    identity = {'skill_version': VERSION, 'skill_sha256': digest(skill), 'schema_sha256': digest(schema),
                'generation_schema_sha256': digest(transport_schema),
                'source_sha256': source['source_sha256'], 'served_model': args.model,
                'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'structured_outputs': {'disable_any_whitespace': True}}
    if (out / 'result.json').exists():
        previous = read(out / 'result.json')
        if previous.get('valid'):
            if previous.get('identity') != identity:
                raise ValueError('Existing successful result has different source/skill/model; choose a new output directory')
            previous_output = read(out / 'output.json')
            if digest(previous_output) != previous.get('output_sha256'):
                raise ValueError('Existing output digest differs from successful result')
            print(packed({'status': 'cached', 'paper_id': source['paper_id'], 'out': str(out)}), flush=True)
            return
    if (out / 'response.json').exists() or (out / 'stream.jsonl').exists():
        raise ValueError('Previous attempt retained here; choose a new output directory instead of overwriting it')
    save(out / 'input.json', source)
    save(out / 'validation-schema.json', schema)
    supplied = {'paper_id': source['paper_id'], 'REFERENCE_BLOCKS': [{'id': b['id'], 'text': b['text']} for b in source['reference_blocks']]}
    system = skill + '\n\nGENERATION_SCHEMA\n' + packed(transport_schema)
    payload = {'model': args.model, 'messages': [{'role': 'system', 'content': system},
               {'role': 'user', 'content': packed(supplied)}], 'temperature': 0, 'seed': 42,
               'max_tokens': args.max_output_tokens, 'chat_template_kwargs': {'enable_thinking': False},
               'response_format': {'type': 'json_schema', 'json_schema': {'name': 'paper_references', 'strict': True, 'schema': transport_schema}},
               'stream': True, 'stream_options': {'include_usage': True}}
    save(out / 'request.json', payload)
    if args.prepare_only:
        print(packed({'status': 'prepared', 'paper_id': source['paper_id'], 'reference_blocks': len(source['reference_blocks']),
                      'input_characters': sum(len(x['text']) for x in source['reference_blocks']), 'out': str(out)}), flush=True)
        return
    if source['reference_blocks']:
        if args.tokenizer_path:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(args.tokenizer_path, local_files_only=True)
            tokens = len(tokenizer.apply_chat_template(payload['messages'], tokenize=True,
                         add_generation_prompt=True, enable_thinking=False))
            save(out / 'budget.json', {'prompt_tokens': tokens, 'max_output_tokens': args.max_output_tokens,
                                      'context_limit': args.context_limit, 'truncate_input': False})
            if tokens + args.max_output_tokens + 512 > args.context_limit:
                raise ValueError('Full bibliography exceeds context/output reserve; retained complete input, no model call')
        response = call_api(args, payload, out)
        generated = json.loads(response['content'], parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        from jsonschema import Draft202012Validator
        Draft202012Validator(schema).validate(generated)
        calls = 1
    else:
        generated = {'references': [], 'unparsed_segments': []}
        response = {'model': args.model, 'usage': {}, 'elapsed_s': 0}
        calls = 0
    save(out / 'generated.json', generated)
    references, unparsed, coverage, errors = materialize(generated, source)
    save(out / 'validation.json', {'valid': not errors, 'errors': errors, 'coverage': coverage,
                                    'checks': ['JSON schema', 'source field literals', 'source order', 'no overlap', 'reference text coverage'],
                                    'semantic_model_review_calls': 0})
    output = {'schema_version': VERSION, 'source': {k: source[k] for k in ['paper_id', 'scope', 'pdf_sha256', 'source_sha256']},
              'references': references, 'unparsed_segments': unparsed, 'coverage': coverage}
    if not errors:
        save(out / 'output.json', output)
    result = {'valid': not errors, 'status': ('empty' if not source['reference_blocks'] else 'partial' if unparsed else 'complete') if not errors else 'failed',
              'identity': identity, 'paper_id': source['paper_id'], 'model_calls': calls, 'review_calls': 0,
              'finished_at': datetime.now(timezone.utc).isoformat(), 'usage': response['usage'],
              'elapsed_s': response['elapsed_s'], 'coverage': coverage, 'errors': errors,
              'output_sha256': digest(output) if not errors else None}
    save(out / 'result.json', result)
    print(packed(result), flush=True)
    if errors:
        raise ValueError('Reference source/coverage validation failed; original response retained')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pp-dir', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--base-url', default='http://127.0.0.1:19361/v1')
    parser.add_argument('--model', default='paper-qwen36-references-v1')
    parser.add_argument('--max-output-tokens', type=int, default=65536)
    parser.add_argument('--timeout', type=int, default=7200)
    parser.add_argument('--tokenizer-path', default=None,
                        help='Local model tokenizer for exact full-input context preflight')
    parser.add_argument('--context-limit', type=int, default=262144)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    try:
        run(args)
    except Exception as exc:
        save(args.out / 'error.json', {'type': type(exc).__name__, 'error': str(exc),
                                     'at': datetime.now(timezone.utc).isoformat()})
        raise


if __name__ == '__main__':
    main()
