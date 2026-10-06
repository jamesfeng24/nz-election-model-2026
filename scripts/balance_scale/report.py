"""Reproducible Stage48 findings document; wording that depends on results is keyed to the decision file."""
from pathlib import Path
from .common import ROOT, PREFIX, arguments, read, verify, RESTRICTIONS

DOC = 'docs/stage48-balance-scale-findings.md'
LABEL = {'control': 'Control C', 'constant': 'Constant K', 'conditional': 'Conditional F'}
COMPARISONS = (('constant_vs_control', 'K vs C'), ('conditional_vs_constant', 'F vs K'), ('conditional_vs_control', 'F vs C'))


def table(header, rows):
    return ['| ' + ' | '.join(header) + ' |', '| ' + ' | '.join('---' for _ in header) + ' |',
            *['| ' + ' | '.join(str(v) for v in r) + ' |' for r in rows], '']


def f(x, digits=3):
    return f'{x:.{digits}f}'


def build():
    fits, ev, dec, ver = (read(PREFIX + '/' + n) for n in ('fit.json', 'evaluation.json', 'decision.json', 'verification.json'))
    comp, cmpd = ev['component'], ev['composed']
    summary = comp['summary']
    out = ['# Stage48: frozen candidate-balance scale comparison, findings', '',
           'Pre-registered design: [stage48-balance-scale-design.md](stage48-balance-scale-design.md), frozen before any restriction other than the corrected control was fitted or scored. '
           'Machine contract: [design-contract.json](../data/processed/balance-scale/design-contract.json). All figures are percentage points unless stated; lower scores are better.', '',
           '## Finding under the frozen rule', '', f'**{dec["finding"]}.** No restriction is adopted: the question bears on the interval widths behind the open probability-release decision, so the choice stays with James. The development default remains the numerically corrected Stage45 Gaussian (control).', '']
    out += ['| Comparison | Delta major CRPS | Delta interval score | Delta energy | Folds improving (of 3) | Resolution (16,384 vs 32,768) | Class |', '| --- | --- | --- | --- | --- | --- | --- |']
    for key, label in COMPARISONS:
        c = dec['component'][key]
        out.append(f'| {label} | {f(c["deltaMajorCRPSPP"], 4)} | {f(c["deltaMajorIntervalScorePP"], 4)} | {f(c["deltaEnergyPP"], 4)} | {c["foldsNegative"]} | {f(c["resolution"]["differencePP"], 5)} ({"pass" if c["resolution"]["passed"] else "fail"}) | **{c["classification"]}** |')
    out += ['', 'Delta major CRPS is the mean over the 193 fitted-fold seats (2017/2020/2023) of the mean CRPS of that seat\'s National and Labour candidates, first minus second; negative favours the first. The 2014 seats are identical across restrictions by design (no earlier data) and contribute exact zeros to the 257-seat values below.', '']
    out += ['## Fitted adjustments', '',
            'Each row is trained only on earlier elections with ridge sd 0.5 on a log-multiplier scale. The multiplier applies to the frozen Stage45 seat balance scale; the shared scale and all other laws are unchanged.', '']
    rows = []
    for year in ('2017', '2020', '2023'):
        fold = fits['folds'][year]
        k, c = fold['constant'], fold['conditional']
        rows.append([year, '/'.join(map(str, fold['trainingYears'])), fold['trainingSeats'], f(k['theta'][0], 4), f(fold['multiplierSummary']['constant']['median'], 4),
                     f'{f(c["theta"][0], 4)} / {f(c["theta"][1], 4)} / {f(c["theta"][2], 4)}',
                     f'{f(fold["multiplierSummary"]["conditional"]["min"], 4)}-{f(fold["multiplierSummary"]["conditional"]["max"], 4)}',
                     f(fold['unpenalisedConstant']['a'], 4), 'none' if not any(k['boundContact'] + c['boundContact']) else 'yes'])
    out += table(['Target', 'Trained on', 'Seats', 'K: a', 'K multiplier', 'F: a / b_R / b_T', 'F multiplier range', 'Unpenalised a (descriptive)', 'Bound contact'], rows)
    out += ['The last-but-one column is the likelihood-only maximiser of a constant, reported only to show how much the frozen penalty restrains the constant. It is not a restriction, was never scored and is not adopted. '
            f'Likelihood information rank is {fits["folds"]["2023"]["conditional"]["likelihoodInformation"]["rank"]} of 3 for F in the last fold (condition number {f(fits["folds"]["2023"]["conditional"]["likelihoodInformation"]["conditionNumber"], 1)}), so the conditional terms are estimable from the likelihood; the penalty still dominates their size. 2014 has no earlier data, so a = b = 0 for all three.', '']
    out += ['## Scores on the 193 fitted-fold seats (32,768 draws)', '']
    pop = summary['fittedFolds']
    rows = [[LABEL[r], f(pop[r]['majorCRPSPP'], 4), f(pop[r]['completeContestEqualCRPSPP'], 4), f(pop[r]['energyPP'], 3), f(pop[r]['forecastPair']['crpsPP'], 4)] for r in RESTRICTIONS]
    out += table(['Restriction', 'Major (N/L) CRPS', 'Complete-slate CRPS', 'Energy', 'Prediction-time margin CRPS'], rows)
    out += ['National and Labour full-interval widths, coverage and interval scores (pooled N/L coordinates):', '']
    rows = []
    for r in RESTRICTIONS:
        for level in ('50', '80', '90'):
            i = pop[r]['majorIntervals'][level]
            p = pop[r]['forecastPair'][level]
            rows.append([LABEL[r], level, f(i['widthPP'], 2), f'{i["covered"]}/{i["total"]}', f(i['coverage'], 3), f(i['intervalScorePP'], 3), f(p['widthPP'], 2), f'{p["covered"]}/{p["total"]}'])
    out += table(['Restriction', 'Level', 'N/L width', 'N/L covered', 'Coverage', 'Interval score', 'Margin width', 'Margin covered'], rows)
    out += ['### By election (major CRPS)', '']
    rows = [[y, *[f(summary[y][r]['majorCRPSPP'], 4) for r in RESTRICTIONS], summary[y]['control']['seats']] for y in ('2014', '2017', '2020', '2023')]
    out += table(['Election', *[LABEL[r] for r in RESTRICTIONS], 'Seats'], rows)
    out += [f'Equal-election mean over the three fitted elections: ' + ', '.join(f'{LABEL[r]} {f(summary["equalElectionFittedFolds"][r]["majorCRPSPP"], 4)}' for r in RESTRICTIONS) + '. '
            f'All 257 seats: ' + ', '.join(f'{LABEL[r]} {f(summary["allSeats"][r]["majorCRPSPP"], 4)}' for r in RESTRICTIONS) + '.', '']
    out += ['## Composed 56-day supporting check (193 seats, 512 draws)', '',
            'Supporting only. Stage47 recorded that composed simulation precision gates are unmet for the control; no fine superiority claim is made.', '']
    rows = []
    for key, label in COMPARISONS:
        c = dec['composed'][key]
        flag = dec['composedSignFlags'].get(key, {}).get('flag')
        rows.append([label, f(c['deltaMajorCRPSPP'], 4), f(c['deltaMajorIntervalScorePP'], 4), f(c['deltaEnergyPP'], 4), c['foldsNegative'], '' if flag is None else ('FLAG' if flag else 'agrees or below flag size')])
    out += table(['Comparison', 'Delta major CRPS', 'Delta interval score', 'Delta energy', 'Folds improving', 'Sign vs conditional bank'], rows)
    out += ['## Numerical checks', '']
    n = dec['numerical']
    rows = [[LABEL[r], 'pass' if n['componentDoublingAllPassed'][r] else 'FAIL', 'pass' if n['composedDoublingAllPassed'][r] else 'FAIL'] for r in RESTRICTIONS]
    out += table(['Restriction', 'Component 8,192 to 16,384 to 32,768 gates (representative seats)', 'Composed 256 to 512 to 1,024 gates'], rows)
    last = {r: comp['representativeDoubling'][r][-1]['changesPP'] for r in RESTRICTIONS}
    out += ['Last component doubling, maximum change over representative seats and candidates (gates 0.05 mean/CRPS, 0.1 energy, 0.5 widths):', '']
    out += table(['Restriction', 'mean', 'crps', 'energy', 'width50', 'width80', 'width90'], [[LABEL[r], *[f(last[r][k], 4) for k in ('mean', 'crps', 'energy', 'width50', 'width80', 'width90')]] for r in RESTRICTIONS])
    last = {r: cmpd['representativeDoubling'][r][-1]['changesPP'] for r in RESTRICTIONS}
    out += ['Last composed doubling:', '']
    out += table(['Restriction', 'mean', 'crps', 'energy', 'width50', 'width80', 'width90'], [[LABEL[r], *[f(last[r][k], 4) for k in ('mean', 'crps', 'energy', 'width50', 'width80', 'width90')]] for r in RESTRICTIONS])
    c47 = ver['controlEqualsStage47Corrected']
    out += [f'Independent checks (all passed): the control equals Stage47\'s sealed corrected bank seat by seat (maximum CRPS difference {c47["component"]["maximumAbsoluteDifference"]["crps"]:.2e} component, {c47["composed"]["maximumAbsoluteDifference"]["crps"]:.2e} composed); non-balance draws and the National+Labour mass are identical across restrictions (maximum gap {n["maximumDrawGapAcrossRestrictions"]:.2e}); composed remainder reuse equals full re-inversion (maximum {ver["reusedRemainderMaximumGap"]:.2e}); conditional-mean gap of every location {ver["locationChecks"]["maximumConditionalMeanGapPP"]:.2e}pp against the 0.05pp gate; maximum finite-bank mean deviation {max(n["maximumFiniteMeanDeviationPP"].values()):.4f}pp.', '']
    k, c0, f_ = pop['constant'], pop['control'], pop['conditional']
    relative = lambda a, b: 100 * (a - b) / b
    mean_is = lambda x: sum(x['majorIntervals'][l]['intervalScorePP'] for l in ('50', '80', '90')) / 3
    unpenalised = [fits['folds'][y]['unpenalisedConstant']['a'] for y in ('2017', '2020', '2023')]
    out += ['## Reading the result', '',
            f'**What the frozen test shows.** The earlier-trained constant (K) beats the corrected control on every pre-registered criterion: major CRPS falls {f(-dec["component"]["constant_vs_control"]["deltaMajorCRPSPP"], 4)}pp ({f(-relative(k["majorCRPSPP"], c0["majorCRPSPP"]), 2)}%), mean N/L interval score {f(-relative(mean_is(k), mean_is(c0)), 2)}% lower, complete-vector energy lower, and all three elections improve (the 2020 fold is the smallest, {f(-dec["component"]["constant_vs_control"]["foldDeltaMajorCRPSPP"]["2020"], 4)}pp). N/L full interval widths narrow by about {f(-relative(k["majorIntervals"]["80"]["widthPP"], c0["majorIntervals"]["80"]["widthPP"]), 1)}% and coverage moves toward nominal at every level (50/80/90: {f(c0["majorIntervals"]["50"]["coverage"], 3)}/{f(c0["majorIntervals"]["80"]["coverage"], 3)}/{f(c0["majorIntervals"]["90"]["coverage"], 3)} to {f(k["majorIntervals"]["50"]["coverage"], 3)}/{f(k["majorIntervals"]["80"]["coverage"], 3)}/{f(k["majorIntervals"]["90"]["coverage"], 3)}). So the candidate balance scale is mildly too conservative on these elections, in the direction the Stage47 attribution suggested.',
            '', f'**What it does not show.** The strongly pooled conditional adjustment (F) adds {f(-dec["component"]["conditional_vs_constant"]["deltaMajorCRPSPP"], 4)}pp over K, far below the 0.01pp threshold and with multipliers spread over only about 1 to 2%, so supported R deficit and historical non-major support do not identify predictable heteroskedasticity here. Under the frozen penalty the conditional terms had little room (|b| at most {f(max(abs(x) for y in ("2017", "2020", "2023") for x in fits["folds"][y]["conditional"]["theta"][1:]), 3)}), so this is "no support under this design", not proof that none exists.',
            '', f'**The penalty limits the size, not only the direction.** The frozen ridge keeps K within 5 to 7% of the frozen scale (multipliers {f(fits["folds"]["2017"]["multiplierSummary"]["constant"]["median"], 3)}, {f(fits["folds"]["2020"]["multiplierSummary"]["constant"]["median"], 3)}, {f(fits["folds"]["2023"]["multiplierSummary"]["constant"]["median"], 3)}). The likelihood alone prefers a constant of {f(unpenalised[0], 3)}, {f(unpenalised[1], 3)}, {f(unpenalised[2], 3)} (multipliers about {f(2.718281828 ** unpenalised[0], 2)}, {f(2.718281828 ** unpenalised[1], 2)}, {f(2.718281828 ** unpenalised[2], 2)}), about three times larger. Stage48 did not score that and the frozen design forbids a prior-strength search, so how much of the remaining over-coverage (N/L 50% coverage is still {f(k["majorIntervals"]["50"]["coverage"], 3)} against 0.5) a weaker penalty would remove is unmeasured. The size of the scale change, the quantity that matters for the open wide-interval question, is not settled by this stage.',
            '', '## Limits', '',
            '- Three fitted folds from reused development elections, chronologically fitted after the fact. This is not untouched validation, and fold-level consistency is the only replication available.',
            f'- 2014 has no earlier data and is prior/control for all three restrictions; the 2014 balance miss (control N/L 50% coverage {f(summary["2014"]["control"]["majorIntervals"]["50"]["coverage"], 3)} that year) is not addressed.',
            '- Composed 56-day simulation precision gates are unmet for every restriction (as for the Stage47 control), so the composed check is supporting direction only. The composed K-versus-C difference is the same sign pooled and in 2020/2023, with 2017 flat (slightly positive).',
            '- Parameter and scale uncertainty remain omitted; the multipliers are point values. The 56-day horizon differs from the roughly 32-day horizon at publication; not measured here.',
            '- Seat-win and winner probabilities were not evaluated, and nothing here is a calibrated probability claim.', '',
            '## Recommendation for James (not adopted)', '',
            '1. **Record the finding; change nothing operational.** Retain the corrected control as the development default. K is a defensible, simple, earlier-trained candidate (about 0.7% lower N/L CRPS, about 3% narrower N/L intervals), but the gain is small, N/L 50% coverage stays near 0.59, and adopting it is a choice about the width question James keeps open.',
            '2. **Close the conditional line.** Do not pursue R-deficit or non-major-support heteroskedasticity further on these data; the frozen test found no signal.',
            '3. **If narrower balance intervals matter, authorise a separate, separately frozen question** on the size of the global constant (for example a single unpenalised or weakly penalised constant against K and the control, with the same scores and a pre-registered rule). The descriptive likelihood suggests a larger effect than K captures, but with three reused folds it should be tested, not assumed, and it would still leave the horizon and composed-precision limits.', '']
    return '\n'.join(out) + '\n'


def main():
    args = arguments()
    verify()
    text = build()
    path = ROOT / DOC
    if args.check:
        if not path.exists() or path.read_text() != text:
            raise ValueError('Stale Stage48 findings document')
    else:
        path.write_text(text)


if __name__ == '__main__':
    main()
