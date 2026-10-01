"""Pinned evidence and deterministic serialization for Stage 23."""
import hashlib
import json
from pathlib import Path

from scripts.boundaries.census_2013 import ROOT

DEST = ROOT / 'data/processed/models/complete-party-vector'
FRAME = 'data/processed/checkpoints/complete-candidate-baseline/input-inventory.json'
CONTINUITY = 'data/processed/models/party-vote-transform/party-continuity.json'
ALLIANCE = 'data/processed/checkpoints/stage21-alliance-mapping/overlay.json'
STAGE5_CONTRACT = 'data/processed/models/party-vote-transform/input-contract.json'


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def digest(path, root=ROOT):
    return hashlib.sha256((root / path).read_bytes()).hexdigest()


def read_json(path, root=ROOT):
    return json.loads((root / path).read_bytes())


def verify_contract(root=ROOT):
    contract = read_json('data/processed/models/complete-party-vector/source-contract.json', root)
    for path, expected in contract['inputHashes'].items():
        if digest(path, root) != expected:
            raise ValueError(f'Changed Stage23 input: {path}')
    return contract


def write_or_check(name, value, check=False):
    path = DEST / name
    raw = encode(value)
    if check:
        if not path.exists() or path.read_bytes() != raw:
            raise ValueError(f'Stale Stage23 {name}')
    else:
        DEST.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
