#!/usr/bin/env python3
"""Run GPT Researcher 0.16.1 with explicit file-relayed model and web tools.

The caller supplies the planner and web responses; this is not an autonomous API
service. Direct socket connections in this process are disabled. Use a new run
directory for each run. See references/web-research.md for the response schemas.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import sys
import time
from datetime import datetime, timezone


def options():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--question', required=True, help='Research question and topic boundary')
    parser.add_argument('--out-dir', type=Path, required=True, help='New directory for the research trace')
    parser.add_argument('--max-queries', type=int, default=4, help='Planner subquery budget, not a result guarantee')
    parser.add_argument('--timeout-seconds', type=float, default=900, help='Timeout for each file response')
    parser.add_argument('--question-id', default='unassigned', help='Question id in the topic coverage plan')
    parser.add_argument('--track', choices=('classic', 'recent', 'unspecified'), default='unspecified')
    parser.add_argument('--cutoff', help='Research cutoff YYYY-MM-DD, recorded for audit')
    parser.add_argument('--seed-file', type=Path, help='Optional UTF-8 context permitted for the planner')
    parser.add_argument('--mode', choices=('live', 'replay'), default='live', help='Label responses as new or replayed')
    args = parser.parse_args()
    if not args.question.strip() or args.max_queries < 1 or args.timeout_seconds <= 0:
        parser.error('Question must be nonempty and budgets must be positive')
    return args


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


async def main(args):
    output = args.out_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=False)
    preflight = {'status': 'blocked', 'mode': args.mode, 'question': args.question,
                 'question_id': getattr(args, 'question_id', 'unassigned'),
                 'track': getattr(args, 'track', 'unspecified'), 'cutoff': getattr(args, 'cutoff', None),
                 'library': 'gpt-researcher==0.16.1', 'verified_papers': 0}
    try:
        version = importlib.metadata.version('gpt-researcher')
    except importlib.metadata.PackageNotFoundError as exc:
        preflight['reason'] = 'sdk_missing'
        write_json(output / 'gptr-run.json', preflight)
        raise RuntimeError('GPT Researcher is not installed in this Python environment') from exc
    if version != '0.16.1':
        preflight.update(reason='sdk_version_mismatch', installed_version=version)
        write_json(output / 'gptr-run.json', preflight)
        raise RuntimeError(f'This bridge targets GPT Researcher 0.16.1; detected {version}. Check compatibility before use.')

    seed = args.seed_file.read_text(encoding='utf-8') if args.seed_file else 'Research using the external search relay.'
    blocked = []
    def deny_socket(_self, address):
        blocked.append(str(address))
        raise RuntimeError('Direct networking is disabled in the file-relay process')
    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex
    socket.socket.connect = deny_socket
    socket.socket.connect_ex = deny_socket
    # Force the customized retriever and memory path; no unrecorded provider calls.
    os.environ['EMBEDDING'] = 'custom:unused-connector-bridge'
    os.environ['RETRIEVER'] = 'custom'
    os.environ['RETRIEVER_ENDPOINT'] = 'http://127.0.0.1:9/disabled'
    os.environ['MAX_ITERATIONS'] = str(args.max_queries)

    trace = {
        'status': 'running', 'library': f'gpt-researcher=={version}',
        'mode': args.mode, 'question': args.question, 'query_budget': args.max_queries,
        'question_id': getattr(args, 'question_id', 'unassigned'),
        'track': getattr(args, 'track', 'unspecified'), 'cutoff': getattr(args, 'cutoff', None),
        'verified_papers': 0, 'coverage_claim': 'unverified candidates only',
        'model_provider': 'supplied by caller via file relay',
        'search_provider': 'supplied by caller via file relay',
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'events': [], 'blocked_direct_network_attempts': blocked,
    }
    write_json(output / 'gptr-run.json', trace)
    counters = {'initial-search': 0, 'planner': 0, 'web-search': 0}

    def request(kind, fields):
        counters[kind] += 1
        suffix = hashlib.sha256(fields.get('query', '').encode()).hexdigest()[:10] if fields.get('query') else 'call'
        name = f'{kind}-{counters[kind]:03d}-{suffix}'
        req, response = output / f'{name}-request.json', output / f'{name}-response.json'
        payload = {'kind': kind, 'response_path': str(response), 'mode': args.mode, **fields}
        write_json(req, payload)
        event = {'kind': kind, 'request': str(req), 'response': str(response),
                 'request_sha256': hashlib.sha256(req.read_bytes()).hexdigest()}
        if 'query' in fields:
            event['query'] = fields['query']
        trace['events'].append(event)
        write_json(output / 'gptr-run.json', trace)
        print('REQUEST', kind, str(req), flush=True)
        return response, event

    def read_response(path, event):
        response = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(response, dict):
            raise ValueError(f'Response must be a JSON object: {path}')
        if not isinstance(response.get('provider'), str) or not response['provider'].strip():
            raise ValueError('Response requires its actual provider name')
        event['provider'] = response['provider']
        event['response_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        event['result_count'] = len(response['results']) if isinstance(response.get('results'), list) else None
        write_json(output / 'gptr-run.json', trace)
        return response

    def wait_sync(path, event):
        deadline = time.monotonic() + args.timeout_seconds
        while not path.is_file():
            if time.monotonic() > deadline:
                raise TimeoutError(f'No file response: {path}')
            time.sleep(.2)
        return read_response(path, event)

    async def wait_async(path, event):
        deadline = time.monotonic() + args.timeout_seconds
        while not path.is_file():
            if time.monotonic() > deadline:
                raise TimeoutError(f'No file response: {path}')
            await asyncio.sleep(.2)
        return read_response(path, event)

    try:
        from langchain_core.documents import Document
        from gpt_researcher import GPTResearcher
        from gpt_researcher.actions import query_processing

        class PublicWebBridge:
            def __init__(self, query, query_domains=None):
                self.query = query

            def search(self, max_results=5):
                path, event = request('initial-search', {'query': self.query, 'max_results': max_results})
                response = wait_sync(path, event)
                if not isinstance(response.get('results'), list):
                    raise ValueError('initial-search response requires a results array')
                return response['results'][:max_results]

        async def relay_model(*_args, **kwargs):
            path, event = request('planner', {'messages': kwargs.get('messages', [])})
            response = await wait_async(path, event)
            if not isinstance(response.get('text'), str) or not response['text'].strip():
                raise ValueError('planner response requires nonempty text')
            return response['text']

        query_processing.create_chat_completion = relay_model
        researcher = GPTResearcher(
            query=args.question, report_type='subtopic_report', report_source='langchain_documents',
            documents=[Document(page_content=seed, metadata={'title': 'Provided research context'})],
            agent='Academic Researcher',
            role='Find relevant research papers and primary sources; distinguish evidence from claims.',
            mcp_strategy='disabled', verbose=False,
        )
        researcher.retrievers = [PublicWebBridge]
        researcher.cfg.max_iterations = args.max_queries

        async def relay_web_context(query, _scraped):
            path, event = request('web-search', {'query': query})
            response = await wait_async(path, event)
            if not isinstance(response.get('results'), list) or not isinstance(response.get('text'), str):
                raise ValueError('web-search response requires results array and text')
            return response['text']

        researcher.context_manager.get_similar_content_by_query = relay_web_context
        context = await researcher.conduct_research()
        write_json(output / 'research-context.json', {'context': context, 'verification': 'unverified', 'mode': args.mode})
        hit_count = sum(e.get('result_count') or 0 for e in trace['events'] if e['kind'] == 'web-search')
        status = 'replayed_unverified' if args.mode == 'replay' else ('retrieved_unverified' if hit_count else 'incomplete')
        trace.update(status=status, context_chars=len(str(context)), candidate_hits=hit_count,
                     actual_subqueries=counters['web-search'])
        print('FINISHED', status, 'subqueries', counters['web-search'], 'context_chars', len(str(context)), flush=True)
    except Exception as exc:
        trace.update(status='failed', error_type=type(exc).__name__)
        raise
    finally:
        socket.socket.connect, socket.socket.connect_ex = original_connect, original_connect_ex
        trace['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(output / 'gptr-run.json', trace)


if __name__ == '__main__':
    try:
        asyncio.run(main(options()))
    except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
