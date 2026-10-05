"""Separate, consumed-input-pinned Stage46 artifacts."""
import argparse
from scripts.uncertainty_revision.common import ROOT, read, encode, digest, equivalent
PREFIX = 'data/processed/uncertainty-tails'
INVENTORY = 'data/processed/uncertainty/inventory.json'
CONTROL = 'data/processed/uncertainty-revision'


def verify():
    for path, expected in read(PREFIX+'/input-contract.json')['inputHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed Stage46 consumed input: '+path)
    for path, expected in read(PREFIX+'/preservation.json')['priorDataHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed prior artifact: '+path)


def save(name, value, check=False):
    path = ROOT/PREFIX/name
    if check:
        if not path.exists() or not equivalent(read(PREFIX+'/'+name), value):
            raise ValueError('Stale Stage46 '+name)
    else:
        path.write_bytes(encode(value))


def arguments():
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true')
    return p.parse_args()


def signature():
    import hashlib
    import sys
    import numpy as np
    import scipy
    paths=sorted((ROOT/'scripts/uncertainty_tails').glob('*.py'))
    return hashlib.sha256(encode({'inputs':read(PREFIX+'/input-contract.json'),
        'specification':digest(PREFIX+'/specification.json'),'scales':digest(PREFIX+'/scales.json'),
        'code':{str(p.relative_to(ROOT)):digest(str(p.relative_to(ROOT))) for p in paths if p.stem not in ('diagnosis','evaluation','verification')},
        'runtime':{'python':list(sys.version_info[:2]),'numpy':np.__version__,'scipy':scipy.__version__,'lock':digest('requirements-boundaries.txt')}})).hexdigest()
