"""Stage73 paths and small helpers. Live code reads only config/nowcast-2026.json and the files it names."""
import hashlib
import json
from fractions import Fraction
import numpy as np
from scripts.uncertainty_revision.common import ROOT, read, encode

CONFIG = 'config/nowcast-2026.json'
OUTPUT = 'data/processed/nowcast-assembly/development-gate.json'
TARGET_FRAME = 'data/processed/forecast-readiness/snapshots/2026-10-05/target-frame.json'
YEAR = 2026
OTHER = 'other'


class AssemblyError(ValueError):
    """A live input is missing, forbidden or inconsistent; the assembly never substitutes a default."""


def require(condition, message):
    if not condition:
        raise AssemblyError(message)


def exact(value):
    return float(Fraction(value['numerator'], value['denominator']))


def namespace_seed(namespace, label):
    """A 32-bit seed derived from the configured seed namespace; never a hand-picked number."""
    return int.from_bytes(hashlib.sha256(f'{namespace}:{label}'.encode()).digest()[:4], 'little')


def permutation(count, namespace, label):
    seed = int.from_bytes(hashlib.sha256(f'{namespace}:{label}'.encode()).digest()[:8], 'little')
    return np.random.default_rng(seed).permutation(count)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def file_sha256(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


__all__ = ['ROOT', 'read', 'encode', 'CONFIG', 'OUTPUT', 'TARGET_FRAME', 'YEAR', 'OTHER', 'AssemblyError', 'require',
           'exact', 'namespace_seed', 'permutation', 'digest', 'file_sha256']
