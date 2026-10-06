"""Stage68 descriptive check: does the national N/L party swing predict the shared candidate-split shift?

python -m scripts.shared_split_swing.run [--check]

Frozen design: docs/stage68-shared-split-swing-design.md. No model layer, mean, scale or forecast changes.
"""
import argparse
import math
import numpy as np
from scripts.balance_scale.common import HETEROGENEITY, equivalent
from scripts.balance_scale.data import environments
from scripts.balance_scale.fit import location
from scripts.uncertainty_revision.common import ROOT, read, encode

PREFIX = 'data/processed/shared-split-swing'


def design():
    return read(PREFIX + '/design-contract.json')


def national_ratio(year):
    """log(N/L) of summed general-electorate party votes."""
    totals = {'nationalparty': 0, 'labourparty': 0}
    for e in read(f'data/processed/elections/{year}.json')['electorates']:
        if e['kind'] != 'general':
            continue
        for p in e['parties']:
            if p['partyKey'] in totals:
                totals[p['partyKey']] += p['votes']
    return math.log(totals['nationalparty'] / totals['labourparty']), totals


def shared_shifts(years):
    env, het = environments(), read(HETEROGENEITY)['records']
    out = {}
    for y in years:
        e = env[y]
        loc, _ = location(e['p'], np.full(len(e['p']), math.hypot(e['seat'], e['shared'])))
        raw = [r['balanceRawResidual'] - r['balanceSeatResidual'] for r in het if r['year'] == y]
        out[y] = {'sharedShift': float(np.mean(e['v'] - loc)), 'seats': len(e['p']), 'heterogeneityElectionMean': float(np.mean(raw))}
    return out


def beta(xs, ys):
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    return float(-(xs @ ys) / (xs @ xs))


def build():
    spec = design()
    years = spec['years']
    shift = shared_shifts(years)
    swing = {}
    for y in years:
        now, totals = national_ratio(y)
        before, _ = national_ratio(spec['previous'][str(y)])
        swing[y] = {'swing': now - before, 'logRatio': now, 'previousLogRatio': before, 'partyVotes': totals}
    x = np.array([swing[y]['swing'] for y in years])
    yv = np.array([shift[y]['sharedShift'] for y in years])
    signs = int(np.sum(np.sign(yv) == -np.sign(x)))
    pooled = beta(x, yv)
    loeo = {}
    for i, y in enumerate(years):
        keep = [j for j in range(len(years)) if j != i]
        b = beta(x[keep], yv[keep])
        loeo[str(y)] = {'beta': b, 'prediction': -b * x[i], 'error': float(yv[i] + b * x[i])}
    loeo_rms = float(np.sqrt(np.mean([v['error'] ** 2 for v in loeo.values()])))
    rms_y = float(np.sqrt(np.mean(yv ** 2)))
    lfo = {}
    for y in spec['stopRule']['leaveFutureOutYears']:
        i = years.index(y)
        b = beta(x[:i], yv[:i])
        lfo[str(y)] = {'trainingYears': years[:i], 'beta': b, 'prediction': -b * x[i], 'absError': float(abs(yv[i] + b * x[i])),
                       'absShift': float(abs(yv[i])), 'beatsZero': bool(abs(yv[i] + b * x[i]) < abs(yv[i]))}
    slope, intercept = np.polyfit(x, yv, 1)
    rule = spec['stopRule']
    tests = {'signsAgree': signs >= rule['signsAgreeRequired'],
             'allLoeoBetaPositive': all(v['beta'] > 0 for v in loeo.values()),
             'loeoRmsRatio': loeo_rms / rms_y <= rule['loeoRmsRatioMaximum'],
             'leaveFutureOutBeatsZero': all(v['beatsZero'] for v in lfo.values())}
    return {'stage': 68, 'decisionNumber': spec['decisionNumber'],
            'finding': rule['findings'][0] if all(tests.values()) else rule['findings'][1], 'tests': tests,
            'byElection': {str(y): {**shift[y], **swing[y]} for y in years},
            'signsAgree': signs, 'pooledBeta': pooled, 'pooledFittedShifts': {str(y): -pooled * swing[y]['swing'] for y in years},
            'leaveOneElectionOut': loeo, 'loeoRms': loeo_rms, 'rmsSharedShift': rms_y, 'loeoRmsRatio': loeo_rms / rms_y,
            'leaveFutureOut': lfo, 'descriptiveWithIntercept': {'slope': float(slope), 'intercept': float(intercept)},
            'notBlind': True, 'operationalAdoption': None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    check = parser.parse_args().check
    summary = build()
    path = ROOT / PREFIX / 'summary.json'
    if check:
        if not equivalent(read(PREFIX + '/summary.json'), summary, 1e-10):
            raise SystemExit('Stale Stage68 summary')
        print('Stage68 summary reproduced')
        return
    path.write_bytes(encode(summary))
    print('Stage68 summary written:', summary['finding'])


if __name__ == '__main__':
    main()
