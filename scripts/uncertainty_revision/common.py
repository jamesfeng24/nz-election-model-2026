"""Pinned consumed inputs and separate, portable Stage45 outputs."""
import argparse
import hashlib
import sys
import numpy as np
import scipy
from scripts.uncertainty.common import ROOT, read, encode, digest, equivalent
from scripts.polling.category_interface.common import portable_gzip

PREFIX = 'data/processed/uncertainty-revision'
OLD = 'data/processed/uncertainty'


def save(name, value, check=False):
    path = ROOT / PREFIX / name
    if check:
        if not path.exists() or not equivalent(read(str(path.relative_to(ROOT))), value):
            raise ValueError('Stale Stage45 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))


def verify():
    contract = read(PREFIX + '/input-contract.json')
    for path, expected in contract['inputHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed consumed input: ' + path)
    for path, expected in read(PREFIX + '/preservation.json')['priorDataHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed prior artifact: ' + path)


def signature():
    paths = sorted((ROOT / 'scripts/uncertainty_revision').glob('*.py'))
    return hashlib.sha256(encode({
        'inputs': read(PREFIX + '/input-contract.json'),
        'consumedCode': {p: digest(p) for p in sorted(read(PREFIX + '/input-contract.json')['inputHashes'])
                         if p.startswith('scripts/')},
        'specification': digest(PREFIX + '/specification.json'),
        'scales': digest(PREFIX + '/scales.json'),
        'code': {str(p.relative_to(ROOT)): digest(str(p.relative_to(ROOT))) for p in paths
                 if p.stem in ('common', 'coordinates', 'estimation', 'simulation', 'construction')},
        'runtime': {'numpy': np.__version__, 'scipy': scipy.__version__,
                    'python': list(sys.version_info[:2]), 'lock': digest('requirements-boundaries.txt')}
    })).hexdigest()


def cache(case_id, value, run_signature):
    path = ROOT / '.cache/stage45' / run_signature / (case_id.replace(':', '-') + '.json.gz')
    raw = portable_gzip(encode(value))
    if path.exists() and path.read_bytes() != raw:
        raise ValueError('Changed deterministic Stage45 cache')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest()}


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    return parser.parse_args()
