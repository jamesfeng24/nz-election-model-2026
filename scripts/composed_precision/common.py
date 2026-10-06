"""Stage54 artifacts, pinned consumed inputs and the frozen design contract."""
import argparse
import math
from scripts.uncertainty_revision.common import ROOT, read, encode, digest

PREFIX = 'data/processed/composed-precision'
DESIGN = PREFIX + '/design-contract.json'
INVENTORY = 'data/processed/uncertainty/inventory.json'
SCALES = 'data/processed/uncertainty-revision/scales.json'
STAGE48_FIT = 'data/processed/balance-scale/fit.json'
STAGE48_EVALUATION = 'data/processed/balance-scale/evaluation.json'
STAGE48_CONTRACT = 'data/processed/balance-scale/design-contract.json'
NATIONAL = 'data/processed/polling/candidate-integration/national/{year}-recent_report_prior.json.gz'
RESTRICTIONS = ('control', 'constant', 'conditional')
YEARS = (2017, 2020, 2023)
CODE = ('scripts/balance_scale/common.py', 'scripts/balance_scale/simulate.py', 'scripts/balance_scale/evaluation.py',
        'scripts/balance_scale/summary.py', 'scripts/uncertainty_expectation/simulation.py',
        'scripts/uncertainty_expectation/integration.py', 'scripts/uncertainty_expectation/audits.py',
        'scripts/uncertainty_tails/streams.py', 'scripts/uncertainty_tails/metrics.py',
        'scripts/uncertainty_tails/integration.py', 'scripts/uncertainty/metrics.py', 'scripts/uncertainty/transforms.py',
        'scripts/uncertainty/construction.py', 'scripts/uncertainty/streams.py',
        'scripts/uncertainty_revision/coordinates.py', 'scripts/uncertainty_revision/estimation.py')
INPUTS = ('docs/stage54-composed-precision-design.md', DESIGN, INVENTORY, SCALES, STAGE48_FIT, STAGE48_EVALUATION,
          STAGE48_CONTRACT, *[NATIONAL.format(year=y) for y in YEARS], *CODE)


def design():
    return read(DESIGN)


def equivalent(expected, actual, tolerance=1e-10, path=''):
    """Exact structure; floats agree to a stated absolute tolerance."""
    if isinstance(expected, dict):
        return (isinstance(actual, dict) and expected.keys() == actual.keys()
                and all(equivalent(v, actual[k], tolerance, path + '.' + k) for k, v in expected.items()))
    if isinstance(expected, list):
        return (isinstance(actual, list) and len(expected) == len(actual)
                and all(equivalent(a, b, tolerance, path) for a, b in zip(expected, actual)))
    if isinstance(expected, float) and isinstance(actual, (float, int)) and not isinstance(actual, bool):
        return math.isfinite(actual) and abs(expected - actual) <= tolerance
    return type(expected) == type(actual) and expected == actual


def save(name, value, check=False, tolerance=1e-10):
    path = ROOT / PREFIX / name
    if check:
        if not path.exists() or not equivalent(read(PREFIX + '/' + name), value, tolerance):
            raise ValueError('Stale Stage54 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))


def pin():
    return {'inputHashes': {p: digest(p) for p in INPUTS}, 'newResources': 0, 'dataSourcesJsonTouched': False}


def verify():
    for path, expected in read(PREFIX + '/input-contract.json')['inputHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed Stage54 consumed input: ' + path)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--pin', action='store_true', help='write input-contract.json for the current consumed inputs')
    args = parser.parse_args()
    if args.pin:
        save('input-contract.json', pin())
        raise SystemExit(0)
    return args
