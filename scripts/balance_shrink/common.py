"""Stage60 artifacts, pinned consumed inputs and the frozen design contract."""
import argparse
from scripts.uncertainty_revision.common import ROOT, read, encode, digest
from scripts.balance_scale.common import equivalent, CODE as STAGE48_SHARED_CODE

PREFIX = 'data/processed/balance-shrink'
DESIGN = PREFIX + '/design-contract.json'
DESIGN_DOC = 'docs/stage60-balance-shrink-design.md'
FINDINGS = 'docs/stage60-balance-shrink-findings.md'
STAGE48 = 'data/processed/balance-scale'
STAGE48_FIT = STAGE48 + '/fit.json'
STAGE48_EVALUATION = STAGE48 + '/evaluation.json'
STAGE48_DESIGN = STAGE48 + '/design-contract.json'
INVENTORY = 'data/processed/uncertainty/inventory.json'
SCALES = 'data/processed/uncertainty-revision/scales.json'
ATTRIBUTION = 'data/processed/uncertainty-expectation/attribution.json'
STAGE48_CODE = tuple(f'scripts/balance_scale/{n}.py' for n in ('common', 'data', 'fit', 'simulate', 'summary', 'evaluation'))
INPUTS = (DESIGN_DOC, DESIGN, 'docs/stage48-balance-scale-design.md', STAGE48_DESIGN, STAGE48_FIT, STAGE48_EVALUATION,
          INVENTORY, SCALES, ATTRIBUTION, 'scripts/uncertainty_revision/coordinates.py', *STAGE48_CODE, *STAGE48_SHARED_CODE)
YEARS = (2014, 2017, 2020, 2023)
LEVELS = (50, 80, 90)


def design():
    return read(DESIGN)


def arms():
    return tuple(design()['armOrder'])


def save(name, value, check=False, tolerance=1e-10):
    path = ROOT / PREFIX / name
    if check:
        if not path.exists() or not equivalent(read(PREFIX + '/' + name), value, tolerance):
            raise ValueError('Stale Stage60 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))


def pin():
    return {'inputHashes': {p: digest(p) for p in INPUTS}, 'newResources': 0, 'dataSourcesJsonTouched': False}


def verify():
    for path, expected in read(PREFIX + '/input-contract.json')['inputHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed Stage60 consumed input: ' + path)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    return parser.parse_args()
