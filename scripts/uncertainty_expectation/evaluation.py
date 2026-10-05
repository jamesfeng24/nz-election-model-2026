"""Scores and width inventories after sealing; numerical repair is not calibration."""
import numpy as np
from scripts.uncertainty_tails.metrics import record, summarize
from .audits import audit_source
from .common import PREFIX, INVENTORY, read, save, verify, arguments
from .construction import signature, arrays, paired_control

METHODS = ('common_control', 'corrected')


def expected_record(row, mean, scope):
    error = 100*(np.asarray(mean)-row['actual'])
    return {'mean': list(mean), 'errorPP': error.tolist(), 'maePP': float(np.mean(abs(error))),
            'msePP2': float(np.mean(error**2)), 'scope': scope}


def score_case(case, lookup):
    records = {m: [] for m in METHODS}
    with arrays(case) as bank, paired_control(case) as control:
        for item in case['records']:
            row = lookup[item['id']]
            meta = item['metadata']
            point = meta.get('deterministicNationalOnlyMean', row['mean'])
            for method, q in (('common_control', control['stage45:'+item['id']][:case['draws']]),
                              ('corrected', bank['corrected:'+item['id']])):
                value = record(row, q, np.asarray(point))
                mean = (meta['conditionalCandidateMeanAfterLocalUncertainty'] if case['layer'] == 'composed'
                        else row['mean']) if method == 'corrected' else q.mean(axis=0).tolist()
                scope = ('Rao-Blackwell candidate conditional mean; finite upstream bank' if case['layer'] == 'composed'
                         else 'frozen conditional arithmetic mean') if method == 'corrected' else 'finite common-bank simulated mean'
                value['expectedShares'] = expected_record(row, mean, scope)
                value['maximumFiniteMeanDeviationPP'] = float(np.max(abs(100*(q.mean(axis=0)-mean))))
                records[method].append(value)
    if [r['id'] for r in records['corrected']] != [r['id'] for r in records['common_control']]:
        raise ValueError('Unequal paired records')
    results = {m: {'records': v, 'summary': summarize(v)} for m, v in records.items()}
    paired = {}
    for field in ('maePP', 'msePP2', 'energyPP'):
        paired[field] = float(np.mean([a[field]-b[field] for a, b in zip(records['corrected'], records['common_control'])]))
    paired['crpsPP'] = float(np.mean([np.mean(a['crpsPP'])-np.mean(b['crpsPP']) for a, b in zip(records['corrected'], records['common_control'])]))
    return {'id': case['id'], 'layer': case['layer'], 'year': case['year'], 'draws': case['draws'],
            'methods': results, 'correctedMinusControl': paired,
            'scoringMeanCaveat': 'Paired ordinary MAE uses both simulated means, isolating numerical-law repair on common streams. Separate corrected expectedShares uses conditional/Rao-Blackwell expectations; control finite mean is not an exact expectation.'}


def monitored(case, lookup):
    scored = score_case(case, lookup)
    result = {}
    for method, value in scored['methods'].items():
        result[method] = []
        for r in value['records']:
            result[method].append({'id': r['id'], 'means': (100*np.asarray(r['simulatedMean'])).tolist(),
                'crps': r['crpsPP'], 'energy': [r['energyPP']],
                **{f'width{v}': r['interval'+str(v)]['widths'] for v in (50, 80, 90)}})
    return result


def precision(construction, candidate_lookup):
    spec = read(PREFIX+'/companion-contract.json')
    by_count = {count: {c['id']: monitored(c, candidate_lookup) for c in construction['representatives'] if c['draws'] == count}
                for count in (256, 512, 1024)}
    rounds = []
    for earlier, later in ((256, 512), (512, 1024)):
        changes = {m: {field: max(abs(a-b) for cid in by_count[later]
            for now, old in zip(by_count[later][cid][m], by_count[earlier][cid][m])
            for a, b in zip(now[field], old[field])) for field in spec['precisionGatesPP']} for m in METHODS}
        passed = {m: all(v <= spec['precisionGatesPP'][field] for field, v in values.items()) for m, values in changes.items()}
        rounds.append({'earlier': earlier, 'later': later, 'changesPP': changes, 'passed': passed})
    return {'representativeSeatsPerElection': 3, 'fullFrameDrawCount': 512, 'cap': 1024,
            'rounds': rounds, 'noToleranceRelaxation': True, 'noCountSelectionFromScores': True,
            'scope': 'representative simulation precision only; conditional integration checked separately for every constructed input',
            'action': 'retain fixed512 full frame; report finite-bank limitations, no fine score/probability claims when gates fail'}


def build():
    construction = read(PREFIX+'/construction.json')
    if construction['signature'] != signature():
        raise ValueError('Corrected producer changed')
    inventory = read(INVENTORY)
    lookups = {layer: {r['targetElectorateId']: r for r in inventory[key]}
               for layer, key in (('local_party', 'partyRecords'), ('candidate', 'candidateRecords'))}
    scored = [score_case(c, lookups['local_party' if c['layer'] == 'local_party' else 'candidate']) for c in construction['cases']]
    pools = {}
    for layer in ('local_party', 'candidate', 'composed'):
        cases = [c for c in scored if c['layer'] == layer]
        pools[layer] = {}
        for method in METHODS:
            rows = [r for c in cases for r in c['methods'][method]['records']]
            pools[layer][method] = {'contestWeighted': summarize(rows),
                'equalElection': {k: float(np.mean([c['methods'][method]['summary'][k] for c in cases]))
                                  for k in ('contestEqualMAEPP', 'contestEqualRMSEPP', 'contestEqualCRPSPP', 'energyPP')},
                'expectedShareMAEPP': float(np.mean([r['expectedShares']['maePP'] for r in rows])),
                'expectedShareRMSEPP': float(np.sqrt(np.mean([r['expectedShares']['msePP2'] for r in rows])))}
    width_cases = {m: [{'id': c['id'], 'year': c['year'], 'layer': c['layer'], 'records': c['methods'][m]['records']}
                      for c in scored if c['layer'] != 'local_party'] for m in METHODS}
    return {'stage': 47, 'signature': signature(), 'cases': scored, 'pooled': pools,
            'widthInventory': {m: audit_source(c) for m, c in width_cases.items()},
            'precision': precision(construction, lookups['candidate']),
            'finiteBankZeroIsNotMathematicalZero': True, 'calibratedWinProbabilities': False,
            'originalStage45': PREFIX+'/original-audit.json', 'statisticalChange': None}


def main():
    args = arguments()
    verify()
    save('evaluation.json', build(), args.check)
    print('Stage47 common-bank scores, major widths and separate precision checks complete')


if __name__ == '__main__':
    main()
