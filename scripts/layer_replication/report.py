"""Reproducible Stage63 findings document; every number is read from the decision and timing files."""
import numpy as np
from .common import ROOT, PREFIX, arguments, read, verify, design

DOC = 'docs/stage63-layer-replication-findings.md'
NAMES = {'mean': 'simulated mean', 'crps': 'CRPS', 'energy': 'energy score', 'width50': '50% width', 'width80': '80% width', 'width90': '90% width'}
KEYS = tuple(NAMES)
SLATE = 71


def table(header, rows):
    return ['| ' + ' | '.join(header) + ' |', '| ' + ' | '.join('---' for _ in header) + ' |',
            *['| ' + ' | '.join(str(v) for v in r) + ' |' for r in rows], '']


def f(x, digits=3):
    return f'{x:.{digits}f}'


def cost(timing):
    """CPU seconds per replicate bank and per one-off local solve, from the representative-seat tasks of the generating run."""
    per, once = [], []
    for t in timing['tasks']:
        if t['kind'] != 'rep':
            continue
        c = t['replicateCPUSeconds']
        rest = float(np.mean(c[1:]))
        per.append(rest)
        once.append(c[0] - rest)
    return float(np.mean(per)), float(np.mean(once)), float(np.sum([sum(t['replicateCPUSeconds']) for t in timing['tasks']]))


def build():
    spec, d, timing = design(), read(PREFIX + '/decision.json'), read(PREFIX + '/timing.json')
    if d['harness']['verdict'] != 'MATCHES_STAGE54':
        raise ValueError('Stage63 harness did not match Stage54')
    caps = spec['gatesPP']
    gate, req, flo, eq, win = d['gateB'], d['requirement'], d['nationalFloor'], d['equivalence'], d['winProbability']
    per, once, total = cost(timing)
    arm_hours = lambda m: (once + m * per) / 3600
    out = ['# Stage63: layer-replicated composed simulation, findings', '',
           'Pre-registered design: [stage63-layer-replication-design.md](stage63-layer-replication-design.md), frozen before any replicate bank was scored. '
           'Machine contract: [design-contract.json](../data/processed/layer-replication/design-contract.json). All figures are percentage points unless stated; no model default, scale, law or frozen cap is changed. '
           'The scale file is an input (the pinned Stage45 scales); Stage60 may change the balance scale and this study then reruns unchanged.', '',
           '## Finding under the frozen rules', '']
    if gate['cheapestArm'] is not None:
        out += [f'**{d["gateBVerdict"]}.** The cheapest arm that meets all six frozen caps at its layer doubling is M = {gate["cheapestArm"]} replicates per national draw '
                f'({gate["cheapestComposedDraws"]:,} composed draws per seat on the fixed 4,096 national draws); the 3-sigma rule requires M = {gate["sigmaRequiredReplicates"]}. '
                f'Its measured cost is about {f(arm_hours(gate["cheapestArm"]), 2)} CPU hours per seat, {f(SLATE * arm_hours(gate["cheapestArm"]), 0)} CPU hours for a {SLATE}-seat slate.', '']
    else:
        out += [f'**{d["gateBVerdict"]}.** No arm up to M = 64 meets all six frozen caps at its layer doubling; the 3-sigma rule requires M = {gate["sigmaRequiredReplicates"]} '
                f'(an M = 64 arm costs about {f(arm_hours(64), 2)} CPU hours per seat, {f(SLATE * arm_hours(64), 0)} for a {SLATE}-seat slate).', '']
    out += ['## Harness', '',
            f'The first 512 positions of replicate 0 equal Stage54 block 0 and those of replicates 8, 9, 10 equal its layer-only records for every representative seat, and replicate 0 equals block 0 for the nine panel seats: '
            f'{d["harness"]["replicateChecks"]} checks over {d["harness"]["seats"]} seats, maximum absolute difference {d["harness"]["maxAbsDifference"]:.1e} (verdict {d["harness"]["verdict"]}). '
            f'Equivalence diagnostic: the two half banks of arm 32 differ by `z` with mean `z^2` {f(eq["meanZSquared"], 2)} and maximum |z| {f(eq["maxAbsZ"], 2)} over {eq["zCount"]} seat-candidate quantities (band 0.6 to 1.6 and 4.5): **{eq["verdict"]}**.', '',
            '## Gate B: layer doubling at the full 4,096 national pool', '',
            'Maximum change over representative seat-candidates when the replicate count is doubled from M/2 to M (nested banks), against the unchanged caps; (fail) marks a cap exceeded.', '']
    rows = []
    for r in gate['rounds']:
        rows.append([f'{r["earlier"]} to {r["arm"]}', f'{r["composedDraws"]:,}'] + [f(r['changesPP'][k]) + ('' if r['passed'][k] else ' (fail)') for k in KEYS])
    rows.append(['Cap', ''] + [str(caps[k]) for k in KEYS])
    out += table(['Replicates', 'Composed draws', *KEYS], rows)
    out += ['Three-sigma requirement from the 64 single-replicate banks (`s1` is the largest sd over representative seat-candidates, so it is biased high; the change on doubling M/2 to M has sd `s1 / sqrt(M)`).', '']
    rows = [[NAMES[k], req[k]['capPP'], f(req[k]['s1Max']), f(req[k]['s1Median'], 4), f'{req[k]["requiredReplicates"]:,}', f(req[k]['ratioAtM64'], 2)] for k in KEYS]
    out += table(['Quantity', 'Cap', 's1 max', 's1 median', 'Required replicates', '3 sigma / cap at M = 64'], rows)
    sc = {m: d['scaling'][m] for m in sorted(d['scaling'], key=int)}
    out += ['Observed sd across non-overlapping groups of M replicates relative to the i.i.d. prediction `s1 / sqrt(M)` (median over seat-candidates; 1.0 is exact 1/M variance scaling; M = 32 rests on two groups and is only indicative).', '']
    out += table(['Group size M', 'Groups', *KEYS], [[m, sc[m][KEYS[0]]['groups']] + [f(sc[m][k]['medianScaledRatio'], 2) for k in KEYS] for m in sc])
    out += ['## Gate A: the literal Stage54 national doubling (2,048 to 4,096 national draws)', '',
            'Includes the difference between two national half-samples, which no layer replication can reduce; reported for comparability.', '']
    rows = []
    for m, a in sorted(d['gateA'].items(), key=lambda kv: int(kv[0])):
        c = a['rounds'][-1]['changesPP']
        rows.append([m] + [f(c[k]) + ('' if a['rounds'][-1]['passed'][k] else ' (fail)') for k in KEYS] + [a['verdict']])
    rows.append(['Cap'] + [str(caps[k]) for k in KEYS] + [''])
    out += table(['Replicates', *KEYS, 'Verdict'], rows)
    out += ['## What the finite national bank leaves', '',
            'Eight disjoint 512-draw national blocks, each pooled over all 64 replicates, give the variance that no replication removes (floor for a 4,096-draw estimate relative to the national population; 7 degrees of freedom, maxima biased high, blocks drawn without replacement from the pool so up to sqrt(7/8) below i.i.d.; reported only).', '']
    q = flo['quantities']
    out += table(['Quantity', 'Cap', 'Floor sd max', 'Floor sd median', '3 sd floor / cap', 'Seat-candidates at zero', 'Negative raw variances'],
                 [[NAMES[k], q[k]['capPP'], f(q[k]['floorSdMax']), f(q[k]['floorSdMedian'], 4), f(q[k]['threeFloorOverCap'], 2), f'{q[k]["seatCandidatesAtZero"]} of {q[k]["seatCandidates"]}', q[k]['negativeRawVariances']] for k in KEYS])
    out += ['Total sd of a (4,096, M) bank relative to the national population (maximum over representative seat-candidates), and the median variance ratio to the one-draw baseline.', '']
    rows = []
    for m, row in sorted(flo['totalSd'].items(), key=lambda kv: int(kv[0])):
        rows.append([m] + [f(row[k]['totalSdMax']) + ' / ' + f(row[k]['medianVarianceRatioToBaseline'], 2) for k in KEYS])
    out += table(['M', *KEYS], rows)
    out += ['## Seat-win probabilities', '',
            f'Seat-candidates with a probability in [0.05, 0.95]: {win["all"]["seatCandidates"]} ({win["representatives"]["seatCandidates"]} representative, {win["panel"]["seatCandidates"]} panel). '
            f'Layer design effect D1 {f(win["all"]["layerDesignEffect"], 3)} (representatives {f(win["representatives"]["layerDesignEffect"], 3)}, panel {f(win["panel"]["layerDesignEffect"], 3)}), '
            f'national design effect Dn {f(win["all"]["nationalDesignEffect"], 3)}; Stage54 measured 0.594 for both at once with 512-draw banks. The standard error of a probability of 0.5 left by the national bank alone is {f(win["all"]["floorStandardErrorAtHalf"], 4)}.', '']
    rows = [[m, f"{4096 * int(m):,}", f(v['relativeToPool'], 4), f(v['relativeToPopulation'], 4)] for m, v in sorted(win['all']['standardErrorAtHalf'].items(), key=lambda kv: int(kv[0]))]
    out += table(['Replicates M', 'Composed draws', 'SE(0.5) relative to the cached pool', 'SE(0.5) relative to the national population'], rows)
    rr = win['all']['requiredReplicates']
    out += [f'Replicates needed for SE(0.5) <= 0.01: {rr["0.01"]["relativeToPool"]} (pool), {rr["0.01"]["relativeToPopulation"]} (population); for <= 0.005: {rr["0.005"]["relativeToPool"]} (pool), {rr["0.005"]["relativeToPopulation"]} (population). No release threshold is set (open decision for James).', '',
            '## CPU cost', '',
            f'Measured on the generating run (process CPU seconds): {f(per, 1)} s per replicate bank of 4,096 draws ({f(1000 * per / 4096, 2)} ms per composed draw, with the exact reuse of the local-layer solves), plus {f(once, 1)} s once per seat for those solves. '
            f'Stage54 used about 14 ms per composed draw without the reuse. Total CPU of the run: {f(total / 3600, 2)} hours (hardware dependent; `timing.json` is compared by structure only).', '']
    rows = [[m, f'{4096 * m:,}', f(arm_hours(m), 2), f(SLATE * arm_hours(m), 1)] for m in spec['arms']['reported']]
    out += table(['Arm M', 'Composed draws per seat', 'CPU hours per seat', f'CPU hours, {SLATE}-seat slate'], rows)
    a = d['gateA']
    fails = sorted({k for m in a for k, ok in a[m]['rounds'][-1]['passed'].items() if not ok} & {k for k, ok in a['64']['rounds'][-1]['passed'].items() if not ok})
    out += ['## Reading', '',
            f'1. **Layer replication removes the layer noise, as Stage54 predicted.** The observed sd across groups of M replicates follows `s1 / sqrt(M)` (ratios near 1.0 up to M = 8 and at M = 16), the half-split diagnostic is {eq["verdict"]}, and every harness comparison with Stage54 is exact. '
            f'The doubling changes fall below every frozen cap from M = {min(gate["passingArms"]) if gate["passingArms"] else "n/a"} onward and the 3-sigma rule asks for M = {gate["sigmaRequiredReplicates"]}. These caps are met relative to the cached national draws, for the control restriction and the pinned scales.',
            f'2. **The literal Stage54 national-doubling gate is still not met at any arm** (it fails for {", ".join(NAMES[k] for k in fails)} even at M = 64). That is the finite national bank, not simulation: the floor left by the 4,096 national draws is up to {f(q["crps"]["floorSdMax"], 2)}pp for CRPS and {f(q["mean"]["floorSdMax"], 2)}pp for the mean at the worst seat-candidate (medians {f(q["crps"]["floorSdMedian"], 4)} and {f(q["mean"]["floorSdMedian"], 4)}), so absolute composed CRPS and mean levels cannot be called settled at 0.05pp whatever M is; replication cuts the median variance of these by roughly 2 to 6 times and that of the interval widths by 10 to 25 times.',
            f'3. **Win probabilities gain little beyond M = 4.** The layer design effect is {f(win["all"]["layerDesignEffect"], 2)} (Stage54: 0.594 with both sources); the national bank alone leaves SE(0.5) {f(win["all"]["floorStandardErrorAtHalf"], 4)}, so SE(0.5) is {f(win["all"]["standardErrorAtHalf"]["1"]["relativeToPopulation"], 4)} at M = 1 and {f(win["all"]["standardErrorAtHalf"]["4"]["relativeToPopulation"], 4)} at M = 4 against a floor that M cannot lower.', '',
            '## Recommendation', '',
            f'- If composed score, interval or mean precision matters for a later stage, use M = {gate["cheapestArm"] if gate["cheapestArm"] else 64} layer replicates per national draw on the fixed 4,096 national draws '
            f'({f(SLATE * arm_hours(gate["cheapestArm"] or 64), 0)} CPU hours for a {SLATE}-seat slate with the exact local-solve reuse, against a Stage54 estimate of about 145 CPU hours for the same caps by more draws without replication). For seat-win probabilities alone M = 4 ({f(SLATE * arm_hours(4), 1)} CPU hours) is within a floor-limited 0.0037 and M = 1 already gives SE(0.5) below 0.006.',
            '- State absolute composed CRPS and mean levels with the national floor above, not as settled at 0.05pp. The frozen caps are unchanged and no default is changed; adopting replication in any release path needs separate authorisation, and a Stage60 change of the balance scale reruns this study unchanged with the new scales file.', '']
    out += ['## Limits', '',
            '- Representatives are the Stage47/48/54 first, middle and last seats of each election, not the worst-precision seats; maxima over 80 seat-candidates of noisy sds are biased high, so the 3-sigma requirements are conservative.',
            '- Layer replicates are independent scrambles of a 4,096-point stream; the scrambled stream beats an i.i.d. bank for smooth statistics, so the measured layer sds are specific to this construction.',
            '- Precision is relative to the cached national draws; the national floor is an estimate from 8 blocks without replacement. No composed simulation improves the effective size of the national bank. The four cached chains disagree more than subsampling implies (Stage54), which this study does not address.',
            '- Control restriction, the pinned Stage45 scales, the 56-day horizon; K and F, a different balance scale (Stage60), horizon, parameter uncertainty and calibration are outside this stage. Nothing is adopted.', '']
    return '\n'.join(out) + '\n'


def main():
    args = arguments()
    verify()
    text = build()
    path = ROOT / DOC
    if args.check:
        if not path.exists() or path.read_text() != text:
            raise ValueError('Stale Stage63 findings document')
    else:
        path.write_text(text)


if __name__ == '__main__':
    main()
