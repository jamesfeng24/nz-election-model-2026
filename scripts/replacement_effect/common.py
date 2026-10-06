"""Pinned inputs, frozen design contract and deterministic artifact IO for Stage55."""
import argparse
import json
import math
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'data/processed/replacement-effect'
DESIGN = PREFIX + '/design-contract.json'
LEDGER = 'data/processed/evidence/candidate-transitions/incumbent-seat-ledger.json'
OCCURRENCES = 'data/processed/models/candidate-overperformance/occurrences.json'
INVENTORY = 'data/processed/uncertainty/inventory.json'
STAGE10_INVENTORY = 'data/processed/models/replacement-candidate/inventory.json'
SCALES = 'data/processed/uncertainty-revision/scales.json'
ELECTIONS = {y: f'data/processed/elections/{y}.json' for y in (2008, 2011, 2014, 2017, 2020, 2023)}
CODE = ('scripts/balance_scale/data.py', 'scripts/balance_scale/fit.py', 'scripts/uncertainty_revision/coordinates.py')
INPUTS = ('docs/stage55-replacement-effect-design.md', DESIGN, LEDGER, OCCURRENCES, INVENTORY, STAGE10_INVENTORY,
          SCALES, *ELECTIONS.values(), *CODE)
FOLD_YEARS = (2017, 2020, 2023)
ARMS = ('C', 'K', 'P', 'T')


def read(path):
    return json.loads((ROOT / path).read_bytes())


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def design():
    return read(DESIGN)


def equivalent(expected, actual, tolerance=1e-9):
    """Exact structure; floats agree to a stated absolute tolerance (platform last bits)."""
    if isinstance(expected, dict):
        return (isinstance(actual, dict) and expected.keys() == actual.keys()
                and all(equivalent(v, actual[k], tolerance) for k, v in expected.items()))
    if isinstance(expected, list):
        return (isinstance(actual, list) and len(expected) == len(actual)
                and all(equivalent(a, b, tolerance) for a, b in zip(expected, actual)))
    if isinstance(expected, float) and isinstance(actual, (float, int)) and not isinstance(actual, bool):
        return math.isfinite(actual) and abs(expected - actual) <= tolerance
    return type(expected) == type(actual) and expected == actual


def save(name, value, check=False):
    path = ROOT / PREFIX / name
    if check:
        if not path.exists() or not equivalent(read(PREFIX + '/' + name), value):
            raise ValueError('Stale Stage55 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))


def pin():
    return {p: digest(p) for p in INPUTS}


def verify():
    for path, expected in read(PREFIX + '/input-contract.json')['inputHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed Stage55 consumed input: ' + path)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='regenerate in memory and compare with the saved artifacts')
    return parser.parse_args()
