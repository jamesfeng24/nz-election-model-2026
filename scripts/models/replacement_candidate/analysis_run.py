"""Generate or verify the Stage 10 non-identifiability analysis."""

import argparse
import hashlib
import json

from scripts.models.replacement_candidate.analysis import analyze, select
from scripts.models.replacement_candidate.outcome_audit import audit, INDEX_PATHS
from scripts.models.replacement_candidate.run import (DEST, ROOT, INPUTS as INVENTORY_INPUTS,
                                                       YEARS, build as build_inventory, digest, encode)
from scripts.validate.source_files import verify_source_files


SOURCE_PLANS = ('data/source-plans/candidate-persistence-sources.json',
                'data/source-plans/freshman-incumbency-tenure-sources.json')
INPUTS = ('data/processed/models/replacement-candidate/inventory.json',
          'data/processed/models/replacement-candidate/input-contract.json',
          'data/processed/models/replacement-candidate/manifest.json',
          'data/processed/models/replacement-candidate/specification.json',
          *INVENTORY_INPUTS, *SOURCE_PLANS, *INDEX_PATHS)


def _read(name):
    return json.loads((ROOT / name).read_bytes())


def _winners():
    result = {}
    for year in YEARS:
        result[year] = {candidate['id'] for seat in _read(f'data/processed/elections/{year}.json')['electorates']
                        for candidate in seat['candidates'] if candidate['elected']}
    return result


def build():
    for name in SOURCE_PLANS:
        verify_source_files(ROOT, _read(name))
    for name, value in build_inventory().items():
        if (DEST / name).read_bytes() != encode(value):
            raise ValueError(f'Changed pinned Stage 10 pre-fit {name}')
    specification = _read('data/processed/models/replacement-candidate/specification.json')
    if (specification['stage'] != 10 or
            specification['inventoryCommit'] != '3e0945b464583039a76c985123395c44ebb70c6f' or
            not specification['freezeStatus'].startswith('frozen after committed pre-fit inventory')):
        raise ValueError('Stage 10 specification was not frozen before analysis')
    records = _read('data/processed/models/replacement-candidate/inventory.json')['records']
    occurrences = _read(INVENTORY_INPUTS[0])['records']
    continuity = _read(INVENTORY_INPUTS[2])['records']
    profiles = _read(INVENTORY_INPUTS[3])['profiles']
    winners = _winners()
    counterfactual = audit(ROOT, records, occurrences, continuity, profiles, winners)
    analysis = analyze(records, counterfactual, set().union(*winners.values()))
    selection = select(analysis)
    inputs = {name: digest(ROOT / name) for name in sorted(set(INPUTS))}
    outputs = {'analysis-input-contract.json': inputs,
               'cohort-audit.json': counterfactual,
               'analysis.json': analysis, 'selection.json': selection}
    code = [ROOT / f'scripts/models/replacement_candidate/{name}.py'
            for name in ('analysis', 'analysis_run', 'outcome_audit')]
    code.extend(ROOT / f'scripts/models/candidate_persistence/{name}.py'
                for name in ('identity', 'official'))
    outputs['analysis-manifest.json'] = {
        'schemaVersion': 1, 'stage': 10, 'phase': 'analysis',
        'inventoryCommit': specification['inventoryCommit'],
        'inputHashes': inputs,
        'codeHashes': {str(path.relative_to(ROOT)): digest(path) for path in code},
        'outputHashes': {name: hashlib.sha256(encode(value)).hexdigest()
                         for name, value in outputs.items()}}
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    if args.check:
        for name, value in outputs.items():
            if (DEST / name).read_bytes() != encode(value):
                raise ValueError(f'Changed Stage 10 analysis output: {name}')
        print('Stage 10 analysis reproducible')
        return
    for name, value in outputs.items():
        (DEST / name).write_bytes(encode(value))
    print('Stage 10 analysis written')


if __name__ == '__main__':
    main()
