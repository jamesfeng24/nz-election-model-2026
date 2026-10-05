"""Separate Stage47 artifacts with consumed-input and preservation contracts."""
import argparse
from scripts.uncertainty_revision.common import ROOT, read, encode, digest, equivalent

PREFIX = 'data/processed/uncertainty-expectation'
INVENTORY = 'data/processed/uncertainty/inventory.json'
SCALES = 'data/processed/uncertainty-revision/scales.json'


def verify():
    for path, expected in read(PREFIX + '/input-contract.json')['inputHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed Stage47 consumed input: ' + path)
    for path, expected in read(PREFIX + '/preservation.json')['priorDataHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed prior artifact: ' + path)


def save(name, value, check=False):
    path = ROOT / PREFIX / name
    if check:
        if not path.exists() or not equivalent(read(str(path.relative_to(ROOT))), value):
            raise ValueError('Stale Stage47 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    return parser.parse_args()
