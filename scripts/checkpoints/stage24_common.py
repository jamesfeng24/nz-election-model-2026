"""Pinned Stage 24 artifacts; earlier checkpoint files remain immutable."""
import hashlib
import json

from scripts.checkpoints import stage22_prefit as prefit
from scripts.models.complete_party_vector.common import verify_contract as verify_stage23

ROOT = prefit.ROOT
DEST = ROOT / 'data/processed/checkpoints/stage24-party-input-substitution'
PREFIX = 'data/processed/checkpoints/stage24-party-input-substitution/'
STAGE22 = 'data/processed/checkpoints/stage22-shared-group-experiment/'
PREFIT = 'data/processed/checkpoints/stage22-shared-group-prefit/'
STAGE23 = 'data/processed/models/complete-party-vector/'
INPUTS = (
    PREFIT + 'amended-fit-contract.json',
    PREFIT + 'amended-features.json',
    PREFIT + 'amended-mapping.json',
    PREFIT + 'manifest.json',
    PREFIT + 'source-contract.json',
    STAGE22 + 'fitted-parameters.json',
    STAGE22 + 'predictions.json',
    STAGE22 + 'actuals.json',  # Evaluation-only: inventory pins bytes, never parses outcomes.
    STAGE22 + 'construction-manifest.json',
    STAGE22 + 'evaluation-manifest.json',
    STAGE23 + 'construction.json',
    STAGE23 + 'source-contract.json',
    STAGE23 + 'specification.json',
    STAGE23 + 'scores.json',  # Previous party diagnostic, not a selection input.
    'scripts/checkpoints/stage22_fit.py',
    'scripts/checkpoints/stage22_construction.py',
)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode()


def read(path):
    return json.loads((ROOT / path).read_bytes())


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def verify_sources():
    expected = read(PREFIT + 'source-contract.json')
    actual = prefit.source_contract(read('data/sources.json'),
        [read(prefit.STAGE20_SOURCES), read(prefit.STAGE21_SOURCES)])
    if expected != actual:
        raise ValueError('Changed Stage22 consumed source contract')
    verify_stage23()


def verify_contract():
    contract = read(PREFIX + 'input-contract.json')
    if set(contract['inputSha256']) != set(INPUTS):
        raise ValueError('Stage24 input dependency set changed')
    for path, expected in contract['inputSha256'].items():
        if digest(path) != expected:
            raise ValueError(f'Changed Stage24 required input: {path}')
    verify_sources()
    return contract


def write_or_check(name, value, check=False):
    raw = encode(value)
    path = DEST / name
    if check:
        if not path.exists() or path.read_bytes() != raw:
            raise ValueError(f'Stale Stage24 artifact: {name}')
    else:
        DEST.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
