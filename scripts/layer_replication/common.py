"""Stage63 artifacts, pinned consumed inputs and the frozen design contract."""
import argparse
from scripts.composed_precision.common import (equivalent, INVENTORY, SCALES, STAGE48_FIT, STAGE48_CONTRACT, STAGE48_EVALUATION,
                                               NATIONAL, YEARS, CODE as STAGE54_CODE, PREFIX as STAGE54)
from scripts.uncertainty_revision.common import ROOT, read, encode, digest

PREFIX = 'data/processed/layer-replication'
DESIGN = PREFIX + '/design-contract.json'
STAGE54_EVALUATION = STAGE54 + '/evaluation.json'
STAGE54_CONTRACT = STAGE54 + '/design-contract.json'
STAGE54_CODE_FILES = tuple('scripts/composed_precision/' + n for n in ('common.py', 'stream.py', 'simulate.py', 'evaluation.py'))
QUANTITIES = ('meansPP', 'crps', 'energy', 'width50', 'width80', 'width90')
GATE_KEY = {'meansPP': 'mean', 'crps': 'crps', 'energy': 'energy', 'width50': 'width50', 'width80': 'width80', 'width90': 'width90'}
VECTOR = ('meansPP', 'crps', 'width50', 'width80', 'width90', 'win')
# the scale file is an input of the method: pointing SCALES_FILE at another pinned scales file reruns the study unchanged
SCALES_FILE = SCALES
INPUTS = ('docs/stage63-layer-replication-design.md', DESIGN, STAGE54_EVALUATION, STAGE54_CONTRACT, INVENTORY, SCALES_FILE, STAGE48_FIT,
          *[NATIONAL.format(year=y) for y in YEARS], *STAGE54_CODE_FILES, *STAGE54_CODE)


def design():
    return read(DESIGN)


def save(name, value, check=False, tolerance=1e-10, structure_only=False):
    path = ROOT / PREFIX / name
    if check:
        if not path.exists():
            raise ValueError('Missing Stage63 artifact: ' + name)
        stored = read(PREFIX + '/' + name)
        ok = (shape(stored) == shape(value)) if structure_only else equivalent(stored, value, tolerance)
        if not ok:
            raise ValueError('Stale Stage63 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))


def shape(value):
    """Keys and list lengths only, for the hardware-dependent timing file."""
    if isinstance(value, dict):
        return {k: shape(v) for k, v in value.items()}
    if isinstance(value, list):
        return [shape(v) for v in value]
    return type(value).__name__ if not isinstance(value, (int, float)) or isinstance(value, bool) else 'number'


def pin():
    return {'inputHashes': {p: digest(p) for p in INPUTS}, 'newResources': 0, 'dataSourcesJsonTouched': False}


def verify():
    for path, expected in read(PREFIX + '/input-contract.json')['inputHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed Stage63 consumed input: ' + path)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--full', action='store_true', help='with --check on the evaluation: replay every replicate, not the bounded sample')
    parser.add_argument('--pin', action='store_true', help='write input-contract.json for the current consumed inputs')
    args = parser.parse_args()
    if args.pin:
        save('input-contract.json', pin())
        raise SystemExit(0)
    return args
