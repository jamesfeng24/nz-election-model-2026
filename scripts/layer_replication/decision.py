"""Apply the frozen Stage63 rules to the stored replicate records; thresholds live in design-contract.json."""
import math
import numpy as np
from .common import PREFIX, QUANTITIES, GATE_KEY, read, save, verify, arguments, design

POOL = 4096
BLOCKS = 8


def vec(record, q):
    return np.atleast_1d(np.asarray(record[q], float))


def nested(seat, m):
    """Arm M: the first M replicates (a group bank of size M, or the whole bank)."""
    if m == seat['replicates']:
        return seat['full']
    return seat['groupBanks'][str(m)][0]


def reps(ev):
    return {k: s for k, s in ev['seats'].items() if s['kind'] == 'rep'}


def next_power_of_two(x, minimum=1):
    return int(max(minimum, 2 ** math.ceil(math.log2(max(x, 1.)))))


def single_sd(seat, q):
    """sd (ddof 1) over the single-replicate banks, per candidate (scalar for energy)."""
    return np.std([vec(r, q) for r in seat['groupBanks']['1']], axis=0, ddof=1)


def max_change(seats, q, a, b):
    """Largest absolute change between two banks over seats and candidates."""
    return max(float(np.max(np.abs(vec(b(s), q) - vec(a(s), q)))) for s in seats.values())


def layer_gate(ev, spec):
    caps, arms = spec['gatesPP'], spec['gateBlayerDoubling']['arms']
    seats = reps(ev)
    rounds = []
    for m in arms:
        change = {GATE_KEY[q]: max_change(seats, q, lambda s: nested(s, m // 2), lambda s: nested(s, m)) for q in QUANTITIES}
        rounds.append({'arm': m, 'earlier': m // 2, 'composedDraws': POOL * m, 'changesPP': change,
                       'ratioToCap': {k: v / caps[k] for k, v in change.items()}, 'passed': {k: change[k] <= caps[k] for k in change},
                       'allPassed': all(change[k] <= caps[k] for k in change)})
    return rounds


def requirement(ev, spec):
    rule, caps = spec['requirement'], spec['gatesPP']
    seats = reps(ev)
    out = {}
    for q in QUANTITIES:
        s1 = max(float(np.max(single_sd(s, q))) for s in seats.values())
        median = float(np.median(np.concatenate([np.atleast_1d(single_sd(s, q)) for s in seats.values()])))
        cap = caps[GATE_KEY[q]]
        raw = (rule['sigmaMultiple'] * s1 / cap) ** 2
        out[GATE_KEY[q]] = {'capPP': cap, 's1Max': s1, 's1Median': median, 'unroundedReplicates': float(raw),
                            'requiredReplicates': next_power_of_two(raw), 'ratioAtM64': float(rule['sigmaMultiple'] * s1 / math.sqrt(64) / cap)}
    return out


def scaling(ev, spec):
    """Observed sd across non-overlapping groups of M replicates relative to the i.i.d. prediction s1 / sqrt(M)."""
    seats = reps(ev)
    out = {}
    for m in [1] + [m for m in spec['arms']['nested'] if 1 < m < 64]:
        row = {}
        for q in QUANTITIES:
            ratios = []
            for s in seats.values():
                groups = np.std([vec(r, q) for r in s['groupBanks'][str(m)]], axis=0, ddof=1)
                ratios.append(np.atleast_1d(groups * math.sqrt(m) / single_sd(s, q)))
            ratios = np.concatenate(ratios)
            row[GATE_KEY[q]] = {'medianScaledRatio': float(np.median(ratios)), 'groups': 64 // m}
        out[str(m)] = row
    return out


def national_doubling(ev, spec):
    caps, counts = spec['gatesPP'], spec['gateAnationalDoubling']['nationalCounts']
    seats = reps(ev)
    out = {}
    for m in spec['gateAnationalDoubling']['arms']:
        rounds = []
        for lo, hi in zip(counts[:-1], counts[1:]):
            change = {GATE_KEY[q]: max_change(seats, q, lambda s: s['nationalDoubling'][str(m)][str(lo)], lambda s: s['nationalDoubling'][str(m)][str(hi)])
                      for q in QUANTITIES}
            rounds.append({'earlier': lo, 'later': hi, 'changesPP': change, 'passed': {k: change[k] <= caps[k] for k in change},
                           'allPassed': all(change[k] <= caps[k] for k in change)})
        last = rounds[-1]
        out[str(m)] = {'rounds': rounds, 'lastDoublingRatioToCap': {k: v / caps[k] for k, v in last['changesPP'].items()},
                       'verdict': 'NATIONAL_DOUBLING_MET' if last['allPassed'] else 'NATIONAL_DOUBLING_NOT_MET'}
    return out


def floor_variance(seat, q):
    """Variance of a 4,096-draw estimate left by the finite national bank (per candidate), unfloored raw value kept."""
    pooled = np.array([vec(b['pooled'], q) for b in seat['blocks']])
    layer = np.array([np.atleast_1d(np.asarray(b['layerSd'][q], float)) for b in seat['blocks']]) ** 2
    raw = pooled.var(axis=0, ddof=1) - layer.mean(axis=0) / seat['replicates']
    return np.maximum(raw, 0.) / BLOCKS, raw


def national_floor(ev, spec):
    caps = spec['gatesPP']
    seats = reps(ev)
    out = {'quantities': {}, 'totalSd': {}}
    parts = {}
    for q in QUANTITIES:
        floors, raws, s1 = [], [], []
        for s in seats.values():
            f, raw = floor_variance(s, q)
            floors.append(f)
            raws.append(raw / BLOCKS)
            s1.append(np.atleast_1d(single_sd(s, q)))
        floors, raws, s1 = np.concatenate(floors), np.concatenate(raws), np.concatenate(s1)
        sd = np.sqrt(floors)
        cap = caps[GATE_KEY[q]]
        out['quantities'][GATE_KEY[q]] = {'capPP': cap, 'floorSdMax': float(sd.max()), 'floorSdMedian': float(np.median(sd)),
                                          'threeFloorOverCap': float(3 * sd.max() / cap), 'seatCandidatesAtZero': int(np.sum(floors == 0)),
                                          'seatCandidates': int(floors.size), 'negativeRawVariances': int(np.sum(raws < 0))}
        parts[q] = (floors, s1)
    for m in spec['arms']['reported'] + [1]:
        row = {}
        for q in QUANTITIES:
            floors, s1 = parts[q]
            total = np.sqrt(floors + s1 ** 2 / m)
            before = floors + s1 ** 2
            row[GATE_KEY[q]] = {'totalSdMax': float(total.max()), 'totalSdMedian': float(np.median(total)),
                                'medianVarianceRatioToBaseline': float(np.median((floors + s1 ** 2 / m)[before > 0] / before[before > 0])),
                                'floorShareOfVarianceAtM': float(np.median((floors / (floors + s1 ** 2 / m))[(floors + s1 ** 2 / m) > 0]))}
        out['totalSd'][str(m)] = row
    return out


def equivalence(ev, spec):
    rule = spec['equivalence']
    arm = rule['halfSplitArm']
    seats = reps(ev)
    z = []
    for s in seats.values():
        a, b = s['groupBanks'][str(arm)][0], s['groupBanks'][str(arm)][1]
        for q in QUANTITIES:
            s1 = np.atleast_1d(single_sd(s, q))
            diff = vec(a, q) - vec(b, q)
            keep = s1 > 0
            z.append(diff[keep] / (s1[keep] * math.sqrt(2 / arm)))
    z = np.concatenate(z)
    ok = bool(rule['meanZSquaredBand'][0] <= np.mean(z ** 2) <= rule['meanZSquaredBand'][1] and np.max(np.abs(z)) <= rule['maxAbsZ'])
    bias = {}
    for q in ('crps', 'energy', 'width50', 'width80', 'width90'):
        diffs, scaled = [], []
        for s in seats.values():
            single = np.mean([vec(r, q) for r in s['groupBanks']['1']], axis=0)
            d = vec(s['full'], q) - single
            diffs.append(np.abs(d))
            scaled.append(np.abs(d) / (np.atleast_1d(single_sd(s, q)) / 8))
        bias[GATE_KEY[q]] = {'maxAbsPP': float(np.max(np.concatenate(diffs))), 'maxInUnitsOfM64Sd': float(np.max(np.concatenate(scaled)))}
    return {'halfSplitArm': arm, 'zCount': int(z.size), 'meanZSquared': float(np.mean(z ** 2)), 'maxAbsZ': float(np.max(np.abs(z))),
            'verdict': 'EQUIVALENT' if ok else 'FLAG', 'finiteBankBiasOfSingleReplicate': bias}


def win_probability(ev, spec):
    rule = spec['winProbability']
    low, high = rule['inclusionRange']
    sets = {'all': ev['seats'], 'representatives': reps(ev), 'panel': {k: s for k, s in ev['seats'].items() if s['kind'] == 'panel'}}
    out = {}
    for name, seats in sets.items():
        layer = nat = denominator = 0.
        count = 0
        for s in seats.values():
            p = vec(s['full'], 'win')
            keep = (p >= low) & (p <= high)
            var1 = np.std([vec(r, 'win') for r in s['groupBanks']['1']], axis=0, ddof=1) ** 2
            floor, _ = floor_variance(s, 'win')
            layer += float(np.sum(POOL * var1[keep]))
            nat += float(np.sum(BLOCKS * 512 * floor[keep]))
            denominator += float(np.sum(p[keep] * (1 - p[keep])))
            count += int(keep.sum())
        d1, dn = layer / denominator, nat / denominator
        entry = {'seatCandidates': count, 'layerDesignEffect': d1, 'nationalDesignEffect': dn,
                 'floorStandardErrorAtHalf': math.sqrt(0.25 * dn / POOL), 'standardErrorAtHalf': {}, 'requiredReplicates': {}}
        for m in spec['arms']['nested']:
            entry['standardErrorAtHalf'][str(m)] = {'relativeToPool': math.sqrt(0.25 * d1 / (POOL * m)),
                                                   'relativeToPopulation': math.sqrt(0.25 * (dn + d1 / m) / POOL)}
        for target in rule['targetStandardErrors']:
            pool = 0.25 * d1 / (POOL * target ** 2)
            population = None if 0.25 * dn / POOL >= target ** 2 else 0.25 * d1 / POOL / (target ** 2 - 0.25 * dn / POOL)
            entry['requiredReplicates'][str(target)] = {'relativeToPool': next_power_of_two(pool),
                                                        'relativeToPopulation': next_power_of_two(population) if population is not None else 'unreachable: national floor'}
        out[name] = entry
    return out


def harness_verdict(ev, spec):
    gaps = {k: s['harness'] for k, s in ev['seats'].items()}
    worst = max(v for h in gaps.values() for v in h.values())
    counts = {'seats': len(gaps), 'replicateChecks': sum(len(h) for h in gaps.values())}
    return {'verdict': 'MATCHES_STAGE54' if worst <= spec['tolerance']['stage54Reproduction'] else 'STOP', 'maxAbsDifference': worst, **counts}


def build():
    spec, ev = design(), read(PREFIX + '/evaluation.json')
    harness = harness_verdict(ev, spec)
    result = {'stage': 63, 'harness': harness, 'operationalAdoption': None}
    if harness['verdict'] != 'MATCHES_STAGE54':
        return result
    rounds = layer_gate(ev, spec)
    required = requirement(ev, spec)
    sigma_arm = max(v['requiredReplicates'] for v in required.values())
    passing = [r['arm'] for r in rounds if r['allPassed']]
    safe = [m for m in passing if m >= sigma_arm]
    if safe and sigma_arm <= 64:
        verdict, cheapest = 'CAPS_MET_BY_REPLICATION', min(safe)
    elif passing:
        verdict, cheapest = 'CAPS_MET_NOT_3SIGMA_SAFE', min(passing)
    else:
        verdict, cheapest = 'CAPS_NOT_MET_BY_64', None
    result.update({'gateB': {'rounds': rounds, 'passingArms': passing, 'sigmaRequiredReplicates': sigma_arm, 'cheapestArm': cheapest,
                             'cheapestComposedDraws': POOL * cheapest if cheapest else None, 'verdict': verdict},
                   'requirement': required, 'scaling': scaling(ev, spec), 'gateA': national_doubling(ev, spec),
                   'nationalFloor': national_floor(ev, spec), 'equivalence': equivalence(ev, spec),
                   'winProbability': win_probability(ev, spec), 'gateBVerdict': verdict})
    return result


def main():
    args = arguments()
    verify()
    save('decision.json', build(), args.check)
    print('Stage63 frozen rules applied' if not args.check else 'Stage63 decision reproduced')


if __name__ == '__main__':
    main()
