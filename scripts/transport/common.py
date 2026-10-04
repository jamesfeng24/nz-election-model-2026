"""Pinned, separate Stage41 companions; historical artifacts are read-only."""
import json
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'data/processed/forecast-transport'
DEST = ROOT / PREFIX
SNAPSHOT = 'data/processed/forecast-readiness/snapshots/2026-10-05/'
LINKS = 'data/processed/evidence/practical-candidate-linkage/'
METHOD = 'baseline_plus_S_plus_R'


def read(path):
    return json.loads((ROOT / path).read_bytes())


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def save(name, value, check=False):
    path = DEST / name
    raw = encode(value)
    if check:
        if not path.exists() or path.read_bytes() != raw:
            raise ValueError('Stale Stage41 companion: '+name)
    else:
        DEST.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def verify_inputs():
    for path, expected in read(PREFIX+'/input-contract.json')['inputHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed consumed input: '+path)


def preserve():
    hashes = read(PREFIX+'/preservation.json')['priorDataHashes']
    for path, expected in hashes.items():
        if digest(path) != expected:
            raise ValueError('Changed earlier data: '+path)
    return len(hashes)
