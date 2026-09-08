"""Immutable local import / checksum-pinned fetch for official historical CSVs.

Import files downloaded through the archive's normal browser links when HTTP clients
receive 403. No cookies, browser profiles or security bypasses are used here.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
YEARS = (2008, 2011, 2014)
LICENSE = 'Crown copyright; accurate reproduction with source acknowledgement permitted: https://www.electionresults.govt.nz/about.html'


def destination(root: Path, year: int, url: str) -> Path:
    parsed = urlparse(url)
    prefix = f'/electionresults_{year}/'
    if year not in YEARS or parsed.scheme != 'https' or parsed.hostname != 'www.electionresults.govt.nz' or not parsed.path.startswith(prefix):
        raise ValueError('Only the three authorized official election archives are allowed')
    relative = Path(parsed.path[len(prefix):])
    if '..' in relative.parts or relative.suffix not in ('.csv', '.html'):
        raise ValueError('Unsafe or unsupported source path')
    return root / 'data/raw/elections' / str(year) / relative


def register(root: Path, year: int, url: str, data: bytes, retrieved_at: str, method: str) -> dict:
    path = destination(root, year, url)
    if not data or data.lstrip().lower().startswith((b'<!doctype html', b'<html')) and path.suffix == '.csv':
        raise ValueError('Empty response or HTML error page instead of CSV')
    digest = hashlib.sha256(data).hexdigest()
    if path.exists() and path.read_bytes() != data:
        raise ValueError('Refusing to overwrite changed authoritative bytes')
    registry_path = root / 'data/sources.json'
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else {'schemaVersion': 1, 'sources': []}
    source_id = 'ec-' + str(year) + '-' + path.relative_to(root / 'data/raw/elections' / str(year)).as_posix().replace('/', '-')
    existing = next((s for s in registry['sources'] if s['id'] == source_id), None)
    if existing and (existing['sha256'] != digest or existing['url'] != url):
        raise ValueError('Source identity/checksum conflict')
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open('xb') as stream:
            stream.write(data)
    if existing:
        return existing
    record = {'schemaVersion': 1, 'id': source_id, 'organisation': ('New Zealand Electoral Commission (historical Chief Electoral Office results for 2008)' if year == 2008 else 'New Zealand Electoral Commission'),
              'url': url, 'dateOrElection': str(year) + ' general election', 'resource': path.name,
              'retrievedAt': retrieved_at, 'rawPath': path.relative_to(root).as_posix(),
              'processingScript': 'scripts/transform/historical.py',
              'limitations': ['Acquisition: ' + method, 'Historical publication; preserve source spelling and rounding. See docs/historical-ingestion.md.'],
              'sha256': digest, 'licence': LICENSE}
    registry['sources'].append(record)
    registry['sources'].sort(key=lambda s: s['id'])
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, choices=YEARS, required=True)
    parser.add_argument('--url')
    parser.add_argument('--file', type=Path)
    parser.add_argument('--retrieved-at')
    parser.add_argument('--fetch-registered', action='store_true')
    args = parser.parse_args()
    if args.fetch_registered:
        sources = json.loads((ROOT / 'data/sources.json').read_text())['sources']
        for source in sources:
            if source['dateOrElection'] != str(args.year) + ' general election':
                continue
            path = ROOT / source['rawPath']
            if path.exists():
                data = path.read_bytes()
            else:
                with urlopen(source['url'], timeout=30) as response:
                    data = response.read()
            if hashlib.sha256(data).hexdigest() != source['sha256']:
                raise ValueError('Checksum mismatch: ' + source['url'])
            register(ROOT, args.year, source['url'], data, source['retrievedAt'], 'checksum-pinned HTTP fetch')
    else:
        if not args.file or not args.url or not args.retrieved_at:
            parser.error('Import requires --file --url --retrieved-at (actual acquisition time, not import time)')
        datetime.fromisoformat(args.retrieved_at.replace('Z', '+00:00'))
        record = register(ROOT, args.year, args.url, args.file.read_bytes(), args.retrieved_at, 'normal browser download; byte-preserving local import')
        print(record['id'], record['sha256'])


if __name__ == '__main__':
    main()
