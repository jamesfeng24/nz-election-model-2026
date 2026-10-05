"""Consumed-input contracts and deterministic separate Stage44 artifacts."""
import argparse
import gzip
from pathlib import Path
from scripts.transport.common import ROOT, digest, encode
from scripts.polling.category_interface.common import portable_gzip

PREFIX = 'data/processed/uncertainty'
YEARS = (2011, 2014, 2017, 2020, 2023)
METHOD = 'baseline_plus_S_plus_R'
SEED = 20261005
DRAWS = 512


def read(path):
    import json
    raw = (ROOT / path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def save(name, value, check=False):
    path = ROOT / PREFIX / name
    raw = encode(value)
    if check:
        if not path.exists() or path.read_bytes() != raw:
            raise ValueError('Stale Stage44 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def cache(name, value):
    path = ROOT / '.cache/stage44' / name
    raw = portable_gzip(encode(value))
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('Changed deterministic uncertainty cache: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    import hashlib
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest()}


def verify():
    for p, expected in read(PREFIX + '/input-contract.json')['inputHashes'].items():
        if digest(p) != expected:
            raise ValueError('Changed consumed input: ' + p)
    hashes = read(PREFIX + '/preservation.json')['priorDataHashes']
    for p, expected in hashes.items():
        if digest(p) != expected:
            raise ValueError('Changed earlier data: ' + p)
    return len(hashes)


def arguments():
    p = argparse.ArgumentParser()
    p.add_argument('--check', action='store_true')
    return p.parse_args()
