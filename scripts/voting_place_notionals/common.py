"""Pinned inputs and deterministic artifact IO for Stage69 (voting-place notional baselines)."""
import argparse
import json
import math
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'data/processed/voting-place-notionals'
RAW = 'data/raw/voting-place-notionals/2026-10-06'
CSV_2023 = 'data/raw/elections/2023/statistics/csv/'

GEOCODE_RAW = RAW + '/nominatim-responses.jsonl'
USER_AGENT = 'nz-election-model-2026-research/1.0 (+https://github.com/jamesfeng24/nz-election-model-2026)'
NOMINATIM = 'https://nominatim.openstreetmap.org/search'
GEOMETRY_2020 = 'data/raw/boundaries/2020-2025/general-2020-geometry.json'
GEOMETRY_2025 = 'data/raw/boundaries/2020-2025/general-2025-geometry.json'


def read(path):
    return json.loads((ROOT / path).read_bytes())


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


RATIO_KEYS = {'numerator', 'denominator'}


def equivalent(expected, actual, tolerance=1e-9):
    """Exact structure; floats agree to a stated absolute tolerance (platform last bits).

    A {numerator, denominator} pair is a rational approximation of a float share (`limit_denominator`), so one last-bit difference
    in the float can change both integers: such pairs are compared by value, to the same tolerance.
    """
    if isinstance(expected, dict) and isinstance(actual, dict) and RATIO_KEYS == set(expected) == set(actual):
        return (expected['denominator'] != 0 and actual['denominator'] != 0
                and abs(expected['numerator'] / expected['denominator'] - actual['numerator'] / actual['denominator']) <= tolerance)
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
            raise ValueError('Stale Stage69 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='regenerate in memory and compare with the saved artifacts')
    return parser.parse_args()
