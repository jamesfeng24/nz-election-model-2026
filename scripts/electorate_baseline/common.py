"""Pinned inputs and deterministic artifact IO for Stage64 (2026 electorate set and notional 2023 baselines)."""
import argparse
import json
import math
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'data/processed/electorate-baseline'
RAW = 'data/raw/electorate-baseline/2026-10-06'
SHEET = RAW + '/tallyroom-nz-2025-redistribution-notional.csv'
ARTICLE = RAW + '/tallyroom-new-zealands-new-electoral-map.html'
CROSSWALK = 'data/processed/boundaries/2023-2026/crosswalk.json'
BOUNDS = 'data/processed/boundaries/2023-2026/party-votes.json'
SCENARIO = 'data/processed/forecast-transport/party-construction.json'
FRAME = 'data/processed/forecast-readiness/snapshots/2026-10-05/target-frame.json'
SCHEDULE_C = 'data/controls/boundaries/2025-population-controls.json'
SCHEDULE_B = 'data/controls/boundaries/2025-change-controls.json'
ELECTION_2023 = 'data/processed/elections/2023.json'
CSV_2023 = 'data/raw/elections/2023/statistics/csv/'
PARTY_BY_ELECTORATE = CSV_2023 + 'votes-for-registered-parties-by-electorate.csv'
OVERALL_SUMMARY = CSV_2023 + 'overall-results-summary.csv'
REGISTRY = PREFIX + '/source-registry.json'
CODE = ('scripts/electorate_baseline/common.py', 'scripts/electorate_baseline/build.py')
INPUTS = (CROSSWALK, BOUNDS, SCENARIO, FRAME, SCHEDULE_C, SCHEDULE_B, ELECTION_2023, PARTY_BY_ELECTORATE,
          OVERALL_SUMMARY, SHEET, ARTICLE, REGISTRY)


def read(path):
    return json.loads((ROOT / path).read_bytes())


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


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
            raise ValueError('Stale Stage64 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))


def pin():
    return {p: digest(p) for p in INPUTS}


def verify():
    for path, expected in read(PREFIX + '/input-contract.json')['inputHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed Stage64 consumed input: ' + path)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='regenerate in memory and compare with the saved artifacts')
    return parser.parse_args()
