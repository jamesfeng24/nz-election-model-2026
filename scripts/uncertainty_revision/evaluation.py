"""Paired scores from sealed uncertainty draws; no construction decisions."""
import numpy as np
from scripts.uncertainty.metrics import record, distribution_summary
from .common import PREFIX, OLD, read, save, verify, arguments, signature
from .construction import arrays


def largest_misses(records):
    options = [(r, i) for r in records for i, covered in enumerate(r['interval90']['covered']) if not covered]
    return [{'id': r['id'], 'option': r['ids'][i], 'group': r['groups'][i],
             'actualPP': 100 * r['actual'][i], 'lowerPP': r['interval90']['lower'][i],
             'upperPP': r['interval90']['upper'][i], 'intervalScorePP': r['interval90']['scores'][i]}
            for r, i in sorted(options, key=lambda x: (-x[0]['interval90']['scores'][x[1]], x[0]['ids'][x[1]]))[:5]]


def build():
    construction = read(PREFIX + '/construction.json')
    if construction['signature'] != signature():
        raise ValueError('Construction changed before scoring')
    inventory = read(OLD + '/inventory.json')
    parties = {r['targetElectorateId']: r for r in inventory['partyRecords']}
    candidates = {r['targetElectorateId']: r for r in inventory['candidateRecords']}
    completed = []
    for case in construction['cases']:
        lookup = parties if case['layer'] == 'local_party' else candidates
        results = {p: [] for p in ('revised', 'unchanged_stage44', 'point')}
        shifts = []
        with arrays(case) as bank:
            for item in case['records']:
                row = lookup[item['id']]
                old_metadata = item['metadata']['unchanged_stage44']
                point = np.array(old_metadata.get('deterministicNationalOnlyMean', row['mean']))
                revised_metadata = item['metadata']['revised']
                if case['layer'] == 'composed' and not np.allclose(point, revised_metadata['deterministicNationalOnlyMean'], rtol=0, atol=1e-12):
                    raise ValueError('Different deterministic comparator')
                for policy in ('revised', 'unchanged_stage44'):
                    q = bank[policy + ':' + row['targetElectorateId']]
                    results[policy].append(record(row, q, point))
                    shifts.append({'id': row['targetElectorateId'], 'policy': policy,
                                   'meanShiftPP': (100 * (q.mean(axis=0) - point)).tolist()})
                results['point'].append(record(row, np.broadcast_to(point, (128, len(point))), point))
        summaries = {p: distribution_summary(records) for p, records in results.items()}
        ids = {p: [r['id'] for r in records] for p, records in results.items()}
        if ids['revised'] != ids['unchanged_stage44'] or ids['revised'] != ids['point']:
            raise ValueError('Different comparison samples')
        paired = {p: float(np.mean([np.mean(r['crpsPP']) - np.mean(c['crpsPP'])
                                  for r, c in zip(results['revised'], results[p])]))
                  for p in ('unchanged_stage44', 'point')}
        completed.append({'id': case['id'], 'layer': case['layer'], 'year': case['year'],
                          'methods': {p: {'summary': summaries[p], 'records': records,
                                          'largest90Misses': largest_misses(records)} for p, records in results.items()},
                          'revisedMinusComparatorCRPSPP': paired, 'meanShifts': shifts})
        print('Scored', case['id'], {p: round(s['contestEqualCRPSPP'], 4) for p, s in summaries.items()}, flush=True)
    pooled = {}
    for layer in ('local_party', 'candidate', 'composed'):
        subset = [c for c in completed if c['layer'] == layer]
        pooled[layer] = {p: {'contestWeighted': distribution_summary([r for c in subset for r in c['methods'][p]['records']]),
                           'equalElectionCRPSPP': float(np.mean([c['methods'][p]['summary']['contestEqualCRPSPP'] for c in subset]))}
                         for p in ('revised', 'unchanged_stage44', 'point')}
    return {'stage': 45, 'constructionSignature': construction['signature'], 'draws': construction['draws'],
            'precisionStatus': construction['precisionStatus'], 'cases': completed, 'pooled': pooled,
            'scoresUseOutcomesOnlyAfterDraws': True, 'operationalSelection': None,
            'calibratedElectorateProbabilities': False}


def main():
    args = arguments(); verify(); save('evaluation.json', build(), args.check)


if __name__ == '__main__':
    main()
