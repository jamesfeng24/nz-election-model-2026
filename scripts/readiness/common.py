"""Dated offline readiness IO and consumed-source integrity."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/processed/forecast-readiness'


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n'


def save(path, value, check=False):
    path = ROOT / path
    text = encoded(value)
    if check:
        if not path.exists() or path.read_text(encoding='utf-8') != text:
            raise ValueError(f'Deterministic reproduction mismatch: {path}')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')


def verify_preservation():
    contract = load('data/processed/forecast-readiness/preservation-contract.json')
    for path, expected in contract['priorDataHashes'].items():
        if digest(path) != expected:
            raise ValueError(f'Prior artifact changed: {path}')
    registry = {s['id']: s for s in load('data/sources.json')['sources']}
    for sid, expected in contract['priorSourceRecordHashes'].items():
        actual = hashlib.sha256(json.dumps(registry[sid], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if actual != expected:
            raise ValueError(f'Prior source record changed: {sid}')
    return {'priorDataFilesUnchanged': len(contract['priorDataHashes']),
            'priorSourceRecordsUnchanged': len(contract['priorSourceRecordHashes'])}


def verify_sources(manifest):
    from scripts.validate.source_files import verify_source_files
    registry = load(manifest['sourceRegistryPath'])
    verify_source_files(ROOT, registry)
    if {s['id'] for s in registry['sources']} != {s['id'] for s in manifest['sources']}:
        raise ValueError('Stage40 manifest/registry membership mismatch')
    if len(manifest['sources']) > manifest['resourceCap'] or len(manifest['queries']) > manifest['queryCap']:
        raise ValueError('Acquisition budget exceeded')
    if len({s['url'] for s in manifest['sources']}) != len(manifest['sources']):
        raise ValueError('Duplicate counted resource')
    for s in manifest['sources'] + manifest['readableExtractions']:
        path = s.get('rawPath', s.get('path'))
        if digest(path) != s['sha256']:
            raise ValueError(f'Source bytes changed: {path}')
        if s['retrievedAt'] > manifest['acquisitionCutoffUTC']:
            raise ValueError('Source after acquisition cutoff')
