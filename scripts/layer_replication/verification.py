"""Independent arithmetic: uncached re-simulation (cache identity), internal identities, plain-loop decisions."""
import numpy as np
from scripts.composed_precision.simulate import composed_bank
from scripts.composed_precision.stream import national_block, POOL
from .common import PREFIX, QUANTITIES, read, save, verify, arguments, design
from .evaluation import seat_row
from .simulate import bank_metrics

# one representative seat and one panel seat, a replicate that is neither 0 nor a Stage54 layer-only scramble
CHECKS = (('nz-general-2017-electorate-01', 3), ('nz-general-2020-electorate-57', 5))


def resimulate(ev):
    """Replicate bank regenerated with the unmodified Stage54 composed_bank (no solve reuse) against the stored record."""
    out = []
    for cid, r in CHECKS:
        year = int(cid.split('-')[2])
        ctx, row = seat_row(year, cid)
        national, _ = national_block(year, ctx['first'], 0, POOL)
        banks, control, _, _ = composed_bank(row, ctx['parties'][cid], national, ctx['pfit'], ctx['fit'], {}, r, ('control',))
        mine = bank_metrics(row, banks['control'], np.asarray(control).mean(axis=0))
        saved = ev['seats'][cid]['groupBanks']['1'][r]
        worst = max(float(np.max(np.abs(np.atleast_1d(mine[k]) - np.atleast_1d(saved[k])))) for k in (*QUANTITIES, 'win'))
        out.append({'id': cid, 'replicate': r, 'maximumAbsoluteDifference': worst})
    return out


def consistency(ev):
    """Identities that hold exactly for linear statistics and for the stored nesting."""
    linear = win_sum = ladder = pooled = 0.
    for s in ev['seats'].values():
        one = s['groupBanks']['1']
        two = s['groupBanks']['2']
        for g in range(len(two)):
            avg = (np.array(one[2 * g]['meansPP']) + np.array(one[2 * g + 1]['meansPP'])) / 2
            linear = max(linear, float(np.max(np.abs(avg - np.array(two[g]['meansPP'])))))
        win_sum = max(win_sum, abs(sum(s['full']['win']) - 1.))
        pooled = max(pooled, float(np.max(np.abs(np.mean([b['pooled']['meansPP'] for b in s['blocks']], axis=0) - np.array(s['full']['meansPP'])))))
        if s['kind'] == 'rep':
            ladder = max(ladder, float(np.max(np.abs(np.array(s['nationalDoubling']['1']['4096']['crps']) - np.array(one[0]['crps'])))),
                         float(np.max(np.abs(np.array(s['nationalDoubling']['64']['4096']['crps']) - np.array(s['full']['crps'])))))
    return {'pairAverageOfMeansMaxAbs': linear, 'winProbabilitiesSumToOneMaxAbs': win_sum, 'blockAverageOfMeansMaxAbs': pooled,
            'nationalLadderTopEqualsGroupBankMaxAbs': ladder}


def plain_decisions(ev, decision):
    """Doubling changes and the layer design effect by explicit loops."""
    out = {}
    seats = [s for s in ev['seats'].values() if s['kind'] == 'rep']
    worst = 0.
    for arm, key in ((64, 'crps'), (16, 'energy')):
        change = 0.
        for s in seats:
            later = s['full'] if arm == s['replicates'] else s['groupBanks'][str(arm)][0]
            earlier = s['groupBanks'][str(arm // 2)][0]
            a, b = np.atleast_1d(later[key]), np.atleast_1d(earlier[key])
            for x, y in zip(a, b):
                change = max(change, abs(x - y))
        name = {'crps': 'crps', 'energy': 'energy'}[key]
        saved = next(r for r in decision['gateB']['rounds'] if r['arm'] == arm)['changesPP'][name]
        worst = max(worst, abs(change - saved))
    out['gateBChange'] = {'difference': worst}
    num = den = 0.
    for s in ev['seats'].values():
        for c, p in enumerate(s['full']['win']):
            if 0.05 <= p <= 0.95:
                series = [r['win'][c] for r in s['groupBanks']['1']]
                mean = sum(series) / len(series)
                num += POOL * sum((v - mean) ** 2 for v in series) / (len(series) - 1)
                den += p * (1 - p)
    out['layerDesignEffect'] = {'plainLoop': num / den, 'difference': abs(num / den - decision['winProbability']['all']['layerDesignEffect'])}
    return out


def build():
    ev, decision = read(PREFIX + '/evaluation.json'), read(PREFIX + '/decision.json')
    if decision['harness']['verdict'] != 'MATCHES_STAGE54':
        raise ValueError('Stage63 harness did not match Stage54; no interpretation')
    tol = design()['tolerance']
    result = {'stage': 63, 'resimulationWithoutSolveReuse': resimulate(ev), 'consistency': consistency(ev), 'plainLoopDecisions': plain_decisions(ev, decision)}
    c = result['consistency']
    result['passed'] = bool(
        all(r['maximumAbsoluteDifference'] <= tol['independentRecompute'] for r in result['resimulationWithoutSolveReuse'])
        and c['pairAverageOfMeansMaxAbs'] <= tol['independentRecompute'] and c['winProbabilitiesSumToOneMaxAbs'] <= 1e-12
        and c['blockAverageOfMeansMaxAbs'] <= tol['independentRecompute']
        and c['nationalLadderTopEqualsGroupBankMaxAbs'] <= 1e-12
        and result['plainLoopDecisions']['gateBChange']['difference'] <= 1e-12
        and result['plainLoopDecisions']['layerDesignEffect']['difference'] <= 1e-9)
    return result


def main():
    args = arguments()
    verify()
    value = build()
    if not value['passed']:
        raise ValueError('Stage63 independent verification failed')
    save('verification.json', value, args.check)
    print('Stage63 independent verification passed')


if __name__ == '__main__':
    main()
