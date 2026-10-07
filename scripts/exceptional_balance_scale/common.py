"""Stage67 artifacts, frozen flags, pinned consumed inputs and the frozen design contract."""
import argparse
import numpy as np
from scripts.uncertainty_revision.common import ROOT, read, encode, digest
from scripts.balance_scale.common import equivalent, HETEROGENEITY
from scripts.balance_shrink.common import INPUTS as STAGE60_INPUTS

PREFIX = 'data/processed/exceptional-balance-scale'
DESIGN = PREFIX + '/design-contract.json'
DESIGN_DOC = 'docs/stage67-exceptional-balance-scale-design.md'
STAGE60 = 'data/processed/balance-shrink'
STAGE60_FIT = STAGE60 + '/fit.json'
STAGE60_CODE = tuple(f'scripts/balance_shrink/{n}.py' for n in ('common', 'evaluation', 'summary', 'decision'))
INPUTS = tuple(dict.fromkeys((DESIGN_DOC, DESIGN, STAGE60_FIT, STAGE60 + '/design-contract.json', HETEROGENEITY,
                              *STAGE60_CODE, *[p for p in STAGE60_INPUTS if p.startswith(('scripts/', 'data/processed/uncertainty'))])))
YEARS = (2014, 2017, 2020, 2023)
DECISION_YEARS = (2017, 2020, 2023)
LEVELS = (50, 80, 90)
FLAG_SETS = {'twogroup': 'primary', 'twogroup17': 'sensitivity'}


def design():
    return read(DESIGN)


def arms():
    return tuple(design()['armOrder'])


def flags(kind):
    """Frozen flag names by year: 'primary' (38) or 'sensitivity' (primary minus the residual-ranked list, 17)."""
    spec = design()['flags']
    primary = {int(y): set(v) for y, v in spec['primary'].items()}
    if kind == 'primary':
        return primary
    listed = {int(y): set(v) for y, v in spec['fromResidualRankedList'].items() if y.isdigit()}
    return {y: primary[y] - listed.get(y, set()) for y in primary}


def names():
    return {r['id']: r['name'] for r in read(HETEROGENEITY)['records']}


def indicator(ids, year, kind, lookup=None):
    """0/1 flag per electorate id; every frozen flag must exist in that year's universe."""
    lookup = lookup or names()
    wanted = flags(kind)[year]
    present = [lookup[i] for i in ids]
    missing = wanted - set(present)
    if missing:
        raise ValueError(f'Frozen Stage67 flag absent from {year}: {sorted(missing)}')
    return np.array([n in wanted for n in present], float)


def save(name, value, check=False, tolerance=1e-10):
    path = ROOT / PREFIX / name
    if check:
        if not path.exists() or not equivalent(read(PREFIX + '/' + name), value, tolerance):
            raise ValueError('Stale Stage67 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))


def pin():
    return {'inputHashes': {p: digest(p) for p in INPUTS}, 'newResources': 0, 'dataSourcesJsonTouched': False}


def verify():
    stored = read(PREFIX + '/input-contract.json')['inputHashes']
    for path, expected in stored.items():
        if digest(path) != expected:
            raise ValueError('Changed Stage67 consumed input: ' + path)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    return parser.parse_args()
