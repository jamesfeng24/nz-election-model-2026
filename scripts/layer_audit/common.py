"""Pinned inputs, frozen design contract and deterministic artifact IO for Stage61."""
import argparse
import json
import math
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'data/processed/layer-audit'
DESIGN = PREFIX + '/design-contract.json'
INVENTORY = 'data/processed/uncertainty/inventory.json'
SCALES = 'data/processed/uncertainty-revision/scales.json'
EVALUATION = 'data/processed/uncertainty-expectation/evaluation.json'
ATTRIBUTION = 'data/processed/uncertainty-expectation/attribution.json'
CODE = ('scripts/uncertainty_revision/coordinates.py', 'scripts/uncertainty_revision/estimation.py', 'scripts/uncertainty/transforms.py')
INPUTS = ('docs/stage61-layer-audit-design.md', DESIGN, INVENTORY, SCALES, EVALUATION, ATTRIBUTION, *CODE)


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
            raise ValueError('Stale Stage61 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))


def pin():
    return {p: digest(p) for p in INPUTS}


def verify():
    for path, expected in read(PREFIX + '/input-contract.json')['inputHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed Stage61 consumed input: ' + path)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='regenerate in memory and compare with the saved artifacts')
    return parser.parse_args()
