"""Stage83 artifacts, frozen flags (Stage67), pinned consumed inputs and the frozen design contract."""
import argparse
from scripts.uncertainty_revision.common import ROOT, read, encode, digest
from scripts.balance_scale.common import equivalent, CODE as STAGE48_CODE
from scripts.exceptional_balance_scale.common import flags as stage67_flags

PREFIX = 'data/processed/ordinary-minor-spread'
DESIGN = PREFIX + '/design-contract.json'
DESIGN_DOC = 'docs/stage83-ordinary-minor-spread-design.md'
INVENTORY = 'data/processed/uncertainty/inventory.json'
SCALES = 'data/processed/uncertainty-revision/scales.json'
STAGE67_CONTRACT = 'data/processed/exceptional-balance-scale/design-contract.json'
STAGE61_CONTRACT = 'data/processed/layer-audit/design-contract.json'
CODE = (*STAGE48_CODE, 'scripts/layer_audit/analysis.py', 'scripts/layer_audit/common.py', 'scripts/balance_shrink/evaluation.py',
        'scripts/balance_scale/fit.py', 'scripts/exceptional_balance_scale/common.py')
INPUTS = tuple(dict.fromkeys((DESIGN_DOC, DESIGN, STAGE67_CONTRACT, STAGE61_CONTRACT, INVENTORY, SCALES, *CODE)))
YEARS = (2014, 2017, 2020, 2023)
DECISION_YEARS = (2017, 2020, 2023)
LEVELS = (50, 80, 90)
# arm -> (flag kind, estimator, uses the mass multiplier)
ARMS = {'within': ('primary', 'moment', False), 'within_mass': ('primary', 'moment', True),
        'within_robust': ('primary', 'robust', False), 'within_mass_robust': ('primary', 'robust', True),
        'within17': ('sensitivity', 'moment', False), 'within_mass17': ('sensitivity', 'moment', True),
        'within_robust17': ('sensitivity', 'robust', False), 'within_mass_robust17': ('sensitivity', 'robust', True)}


def design():
    return read(DESIGN)


def arms():
    return tuple(design()['armOrder'])


def flags(kind):
    return stage67_flags(kind)


def is_flagged(row, kind):
    return row['name'] in flags(kind)[int(row['targetYear'])]


def check_flags_present(rows_by_year):
    """Every frozen flag must name a seat that exists in that year's universe."""
    for kind in ('primary', 'sensitivity'):
        for year, wanted in flags(kind).items():
            missing = wanted - {r['name'] for r in rows_by_year[year]}
            if missing:
                raise ValueError(f'Frozen Stage67 flag absent from {year}: {sorted(missing)}')


def save(name, value, check=False, tolerance=1e-10):
    path = ROOT / PREFIX / name
    if check:
        if not path.exists() or not equivalent(read(PREFIX + '/' + name), value, tolerance):
            raise ValueError('Stale Stage83 artifact: ' + name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(value))


def pin():
    return {'inputHashes': {p: digest(p) for p in INPUTS}, 'newResources': 0, 'dataSourcesJsonTouched': False}


def verify():
    for path, expected in read(PREFIX + '/input-contract.json')['inputHashes'].items():
        if digest(path) != expected:
            raise ValueError('Changed Stage83 consumed input: ' + path)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    return parser.parse_args()
