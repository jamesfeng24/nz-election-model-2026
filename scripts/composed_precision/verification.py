"""Independent arithmetic: Stage48 block-0 identity, deterministic re-simulation, internal consistency, plain-loop decisions."""
import numpy as np
from scripts.uncertainty.construction import scale_for
from .common import PREFIX, INVENTORY, SCALES, STAGE48_EVALUATION, RESTRICTIONS, YEARS, read, save, verify, arguments, design
from .evaluation import year_inputs, national_block
from .simulate import composed_bank, summarize_bank


def major(groups):
    return [i for i, g in enumerate(groups) if g in ('national', 'labour')]


def stage48_block_zero(ev):
    """Block 0 against Stage48's stored composed records, re-aggregated here with plain loops."""
    stored = read(STAGE48_EVALUATION)['composed']['records']
    worst = {'majorCRPSPP': 0., 'energyPP': 0., 'intervalScorePP': 0.}
    for r in RESTRICTIONS:
        for rec in stored[r]:
            lean = ev['seats'][rec['id']]['blocks']['0'][r]
            m = major(rec['groups'])
            worst['majorCRPSPP'] = max(worst['majorCRPSPP'], abs(sum(rec['crpsPP'][i] for i in m) / len(m) - lean['majorCRPSPP']))
            worst['energyPP'] = max(worst['energyPP'], abs(rec['energyPP'] - lean['energyPP']))
            for k, level in enumerate((50, 80, 90)):
                mean = sum(rec[f'interval{level}']['scores'][i] for i in m) / len(m)
                worst['intervalScorePP'] = max(worst['intervalScorePP'], abs(mean - lean['intervalScorePP'][k]))
    return {'seatsPerRestriction': len(stored['control']), 'maximumAbsoluteDifference': worst}


def resimulate(ev):
    """A representative seat and an all-seat seat regenerated on a block that was not used for the harness check."""
    ctx = year_inputs(2017)
    rows = {r['targetElectorateId']: r for r in ctx['rows']}
    out = []
    for cid, block in ((ctx['rows'][0]['targetElectorateId'], 5), (ctx['rows'][-1]['targetElectorateId'], 2)):
        row = rows[cid]
        national, _ = national_block(2017, ctx['first'], block)
        restrictions = RESTRICTIONS if block < 4 else RESTRICTIONS[:1]
        banks, control_input, rb, _ = composed_bank(row, ctx['parties'][cid], national, ctx['pfit'], ctx['fit'], ctx['mult'](cid), block, restrictions)
        point = control_input.mean(axis=0)
        seat = ev['seats'][cid]
        for r in restrictions:
            lean, _ = summarize_bank(row, banks[r], point, rb if r == 'control' else None)
            saved = seat['blocks'][str(block)][r] if block < 4 else seat['representativeBlocks'][str(block)]
            worst = max(abs(a - b) for k in ('majorCRPSPP', 'energyPP') for a, b in [(lean[k], saved[k])])
            worst = max(worst, max(abs(a - b) for k in ('intervalScorePP', 'majorWidthPP', 'majorMeanPP', 'majorWin') for a, b in zip(lean[k], saved[k])))
            out.append({'id': cid, 'block': block, 'restriction': r, 'maximumAbsoluteDifference': float(worst)})
    return out


def consistency(ev):
    """Internal identities of the stored records."""
    ladder = 0.
    for cid, rep in ev['representatives'].items():
        first = ev['seats'][cid]['blocks']['0']['control']
        stored = rep['ladder']['512']
        ladder = max(ladder, max(abs(a - b) for a, b in zip(stored['crps'], first['crpsPP'])), abs(stored['energy'] - first['energyPP']),
                     max(abs(a - b) for a, b in zip(stored['meansPP'], first['meanPP'])))
    win_sum, distinct, draws = 0., True, set()
    for seat in ev['seats'].values():
        for block, rec in seat['blocks'].items():
            win_sum = max(win_sum, abs(sum(rec['control']['win']) - 1.))
        distinct = distinct and seat['blocks']['0']['control']['crpsPP'] != seat['blocks']['1']['control']['crpsPP']
    for rep in ev['representatives'].values():
        draws.add(tuple(sorted((c, v['draws']) for c, v in rep['chains'].items())))
    return {'ladder512EqualsBlockZeroMaxAbs': float(ladder), 'winProbabilitiesSumToOneMaxAbs': float(win_sum),
            'blockOneDiffersFromBlockZeroEverySeat': bool(distinct),
            'chainDrawCounts': [list(map(list, d)) for d in sorted(draws)]}


def plain_decisions(ev, decision):
    """Pooled K-minus-C block values and the design effect by explicit loops."""
    out = {}
    for name, (x, y) in {'constant_vs_control': ('constant', 'control'), 'conditional_vs_constant': ('conditional', 'constant')}.items():
        values = []
        for block in ('0', '1', '2', '3'):
            total, count = 0., 0
            for seat in ev['seats'].values():
                total += seat['blocks'][block][x]['majorCRPSPP'] - seat['blocks'][block][y]['majorCRPSPP']
                count += 1
            values.append(total / count)
        saved = decision['settled'][name]['deltaMajorCRPSPP']['blockValues']
        out[name] = {'plainLoop': values, 'difference': max(abs(a - b) for a, b in zip(values, saved))}
    num = den = 0.
    for seat in ev['seats'].values():
        n_cand = len(seat['blocks']['0']['control']['win'])
        for c in range(n_cand):
            series = [seat['blocks'][b]['control']['win'][c] for b in ('0', '1', '2', '3')]
            p = sum(series) / 4
            if 0.05 <= p <= 0.95:
                num += 512 * sum((v - p) ** 2 for v in series) / 3
                den += p * (1 - p)
    out['designEffect'] = {'plainLoop': num / den, 'difference': abs(num / den - decision['winProbability']['designEffect'])}
    return out


def build():
    ev, decision = read(PREFIX + '/evaluation.json'), read(PREFIX + '/decision.json')
    if decision['harness']['verdict'] != 'MATCHES_STAGE48':
        raise ValueError('Stage54 harness did not match Stage48; no interpretation')
    tol = design()['tolerance']
    result = {'stage': 54, 'stage48BlockZero': stage48_block_zero(ev), 'resimulation': resimulate(ev), 'consistency': consistency(ev),
              'plainLoopDecisions': plain_decisions(ev, decision)}
    result['passed'] = bool(
        max(result['stage48BlockZero']['maximumAbsoluteDifference'].values()) <= tol['stage48Block0']
        and all(r['maximumAbsoluteDifference'] <= tol['independentRecompute'] for r in result['resimulation'])
        and result['consistency']['ladder512EqualsBlockZeroMaxAbs'] <= tol['independentRecompute']
        and result['consistency']['winProbabilitiesSumToOneMaxAbs'] <= 1e-12
        and result['consistency']['blockOneDiffersFromBlockZeroEverySeat']
        and all(d == [[c, 1024] for c in ('1', '2', '3', '4')] for d in result['consistency']['chainDrawCounts'])
        and all(v['difference'] <= 1e-9 for v in result['plainLoopDecisions'].values()))
    return result


def main():
    args = arguments()
    verify()
    value = build()
    if not value['passed']:
        raise ValueError('Stage54 independent verification failed')
    save('verification.json', value, args.check)
    print('Stage54 independent verification passed')


if __name__ == '__main__':
    main()
