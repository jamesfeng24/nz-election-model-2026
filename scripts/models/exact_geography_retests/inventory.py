"""Freeze Stage27 IDs, permitted covariates and scenario gates before fitting."""
from collections import Counter

from scripts.checkpoints import stage25_availability as available
from scripts.checkpoints.stage22_fit import SCENARIOS
from . import adapters as a
from .common import (DEST, ROOT, GEO, INPUTS, OLD_RESPONSE, cli, digest, read,
                     preservation_snapshot, save_outputs, verify_preservation)


def outputs():
    elections, splits = a.datasets()
    data = a.inventory(elections, splits, read(GEO + 'geography.json'),
                       read(GEO + 'availability.json'), read(available.MAPPING),
                       read(available.CONTINUITY)['records'])
    folds = [f for f in read(GEO + 'fold-plan.json')['folds']
             if f['family'] in ('nat_lab_response', 'complete_share_baseline_s')]
    gates = []
    for f in folds:
        family_rows = data['shareRecords'] if f['family'] == 'complete_share_baseline_s' else data['responseRecords']
        for label, key in (('expanded', 'trainingIds'), ('original_only', 'originalTrainingIds')):
            train, test = a.permitted_fold(f, family_rows, key)
            row = {'foldId': f['foldId'], 'trainingVariant': label,
                   'trainingIds': f[key], 'evaluationIds': f['evaluationIds'],
                   'trainingCount': len(train), 'evaluationCount': len(test)}
            if f['family'] == 'complete_share_baseline_s':
                row['scenarios'] = {}
                for scenario in SCENARIOS:
                    if not train:
                        row['scenarios'][scenario] = {'status': 'abstain', 'reason': 'no_earlier_training_transition'}
                        continue
                    means = a.s_means(train, scenario)
                    tg = a.rank_gate(train, means, scenario)
                    eg = a.rank_gate(test, means, scenario)
                    row['scenarios'][scenario] = {'trainingOnlyMeans': means, 'training': tg,
                                                  'evaluation': eg, 'passes': tg['passes'] and eg['passes']}
            gates.append(row)
    source = read(GEO + 'source-contract.json')
    available.verify_contract(source)
    inputs = {'stage': 27, 'status': 'frozen_before_fits_and_scores',
              'informationSet': 'retrospective_conditional_observed_target_local_party',
              'inputSha256': {p: digest(p) for p in INPUTS},
              'sourceDependencies': GEO + 'source-contract.json',
              'planSha256': digest('docs/stage27-exact-geography-plan.md'),
              'responseModels': read(OLD_RESPONSE + 'specification.json')['models'],
              'candidateModels': ['baseline', 'baseline_plus_S'],
              'operationalSelection': None}
    summary = []
    for year in sorted({r['targetYear'] for r in data['fullFrame']}):
        records = [r for r in data['fullFrame'] if r['targetYear'] == year]
        rows = [r for r in data['shareRecords'] if r['targetYear'] == year]
        summary.append({'targetYear': year, 'fullFrameContests': len(records),
                        'reasons': dict(sorted(Counter(r['reason'] or r['status'] for r in records).items())),
                        'constructedContests': len(rows),
                        'candidates': sum(len(r['candidates']) for r in rows),
                        'sSupportedCandidates': sum(c['s0Reported'] is not None for r in rows for c in r['candidates']),
                        'sFallbackCandidates': sum(c['s0Reported'] is None for r in rows for c in r['candidates']),
                        'responseRecords': sum(r['targetYear'] == year for r in data['responseRecords'])})
    snapshot_path = ROOT / DEST / 'prior-data-contract.json'
    snapshot = read(DEST + 'prior-data-contract.json') if snapshot_path.exists() else preservation_snapshot()
    verify_preservation(snapshot)
    return {'input-contract.json': inputs, 'inventory.json': data,
            'folds.json': {'folds': folds, 'preFitGates': gates},
            'coverage.json': {'records': summary}, 'prior-data-contract.json': snapshot}


def main():
    result = outputs()
    save_outputs(result, cli())
    print(result['coverage.json'])


if __name__ == '__main__':
    main()
