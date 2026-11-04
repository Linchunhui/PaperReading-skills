#!/usr/bin/env python3
"""Crop a visually selected PDF page rectangle and record its provenance.

Rectangle coordinates are pixels on the full page rendered at --dpi. Inspect
the complete page first: a successful crop does not prove it contains the right
figure or retains the figure's full labels and legend.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def call(command):
    env = dict(os.environ, LC_ALL='C')
    try:
        return subprocess.run(command, text=True, capture_output=True, env=env, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f'Required tool not found: {command[0]}') from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f'{command[0]} failed: {exc.stderr.strip()}') from exc


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--page', type=int, required=True, help='Physical PDF page number, starting at 1')
    parser.add_argument('--figure', required=True, help='Figure number in the selected PDF version')
    parser.add_argument('--box-px', type=int, nargs=4, metavar=('X', 'Y', 'WIDTH', 'HEIGHT'), required=True)
    parser.add_argument('--dpi', type=int, default=144, help='Same DPI used to inspect the full page')
    parser.add_argument('--output', type=Path, required=True, help='New PNG path')
    parser.add_argument('--manifest', type=Path, help='Optional new JSON metadata path')
    parser.add_argument('--version', help='Version identifier as independently verified by the caller')
    args = parser.parse_args()
    x, y, w, h = args.box_px
    if args.page < 1 or args.dpi < 1 or x < 0 or y < 0 or w < 1 or h < 1:
        parser.error('page, dpi, width and height must be positive; x and y must be nonnegative')
    if args.output.suffix.lower() != '.png' or not args.figure.strip():
        parser.error('output must be a PNG and figure must be nonempty')
    return args


def main(args):
    pdf, output = args.pdf.expanduser().resolve(), args.output.expanduser().resolve()
    manifest = args.manifest.expanduser().resolve() if args.manifest else None
    if not pdf.is_file():
        raise ValueError(f'PDF missing or invalid: {pdf}')
    with pdf.open('rb') as stream:
        header = stream.read(1024)
    if b'%PDF-' not in header:
        raise ValueError(f'PDF missing or invalid: {pdf}')
    if output == pdf or (manifest and manifest in (pdf, output)):
        raise ValueError('PDF, PNG, and manifest must be different files')
    for path in (output, manifest):
        if path and path.exists():
            raise FileExistsError(f'Refusing to overwrite existing file: {path}')
    info = call(['pdfinfo', str(pdf)]).stdout
    match = re.search(r'^Pages:\s*(\d+)\s*$', info, flags=re.M)
    if not match:
        raise ValueError('Could not read PDF page count')
    count = int(match[1])
    if args.page > count:
        raise ValueError(f'PDF has {count} pages, requested {args.page}')
    output.parent.mkdir(parents=True, exist_ok=True)
    if manifest:
        manifest.parent.mkdir(parents=True, exist_ok=True)
    x, y, w, h = args.box_px
    with tempfile.TemporaryDirectory(prefix='paper-figure-', dir=output.parent) as directory:
        prefix = Path(directory) / 'crop'
        call(['pdftoppm', '-f', str(args.page), '-l', str(args.page), '-r', str(args.dpi),
              '-png', '-singlefile', '-x', str(x), '-y', str(y), '-W', str(w), '-H', str(h),
              str(pdf), str(prefix)])
        crop = prefix.with_suffix('.png')
        header = crop.read_bytes()[:24]
        if len(header) < 24 or header[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError('Renderer did not produce a valid PNG')
        width, height = struct.unpack('>II', header[16:24])
        if (width, height) != (w, h):
            raise ValueError(f'Crop {width}x{height} does not match requested {w}x{h}; check page bounds and DPI')
        metadata = {'source_pdf': str(pdf), 'source_sha256': sha256(pdf), 'source_version': args.version,
                    'page': args.page, 'page_count': count, 'figure': args.figure,
                    'dpi': args.dpi, 'box_px': {'x': x, 'y': y, 'width': w, 'height': h},
                    'png': str(output), 'png_sha256': sha256(crop),
                    'created_at_utc': datetime.now(timezone.utc).isoformat(),
                    'visual_review': 'required: verify figure number, complete crop, and caption'}
        # The temporary crop lives on the same filesystem; link fails if output
        # appeared concurrently, so an existing user file is never overwritten.
        os.link(crop, output)
        if manifest:
            with manifest.open('x', encoding='utf-8') as stream:
                stream.write(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main(parse_args())
    except (OSError, RuntimeError, ValueError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
