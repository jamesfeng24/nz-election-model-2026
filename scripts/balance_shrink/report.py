"""Reproducible Stage60 findings document; wording that depends on results is keyed to the decision file."""
from .common import ROOT, PREFIX, FINDINGS, YEARS, arguments, read, verify, arms

LABEL = {'control': 'control (1.00)', 'grid95': 'grid 0.95', 'grid90': 'grid 0.90', 'grid85': 'grid 0.85', 'grid80': 'grid 0.80',
         'free': 'free (earlier-trained, penalty-free)', 'penalised': 'Stage48 K (reference)'}


def table(header, rows):
    return ['| ' + ' | '.join(header) + ' |', '| ' + ' | '.join('---' for _ in header) + ' |',
            *['| ' + ' | '.join(str(v) for v in r) + ' |' for r in rows], '']


def f(x, digits=3):
    return f'{x:.{digits}f}'


def pct(x, digits=1):
    return f'{100 * x:.{digits}f}%'


def build():
    fits, ev, dec, ver = (read(PREFIX + '/' + n) for n in ('fit.json', 'evaluation.json', 'decision.json', 'verification.json'))
    order, S = arms(), dec['summary']
    candidates = [a for a in order if a not in ('control', 'penalised')]
    sel = dec['selection']
    finding = dec['finding']
    out = ['# Stage60: stronger candidate-balance scale test, findings', '',
           'Pre-registered design: [stage60-balance-shrink-design.md](stage60-balance-shrink-design.md), frozen (commit `30beda3`) before any Stage60 arm was simulated or scored. '
           'Machine contract: [design-contract.json](../data/processed/balance-shrink/design-contract.json). All figures are percentage points unless stated; lower scores are better. '
           'Decision seats are the 193 general-electorate seats of 2017, 2020 and 2023; 2014 is reported separately. Māori electorates are excluded by electorate type (none are in the candidate inventory).', '',
           '## Finding under the frozen rule', '']
    if finding.startswith('recommend_'):
        arm = sel['recommended']
        kind = 'fitted on earlier elections only (leave-future-out)' if dec['recommendedArmIsLeaveFutureOut'] else 'a fixed grid value, development-informed (not held out)'
        out += [f'**{finding}.** The recommended arm is **{LABEL[arm]}**, {kind}. This is a recommendation only: the corrected control remains the default until James signs off, and nothing is adopted.', '']
    elif finding == 'floor_blocked_report_to_james':
        out += [f'**{finding}.** At least one arm improves the scores but every such arm breaks the coverage floor. No recommendation; reported to James. Nothing is adopted.', '']
    else:
        out += [f'**{finding}.** No arm passes Stage48\'s IMPROVES rule against the control. Nothing is adopted.', '']
    out += ['Each arm against the control on the 193 decision seats. Delta major CRPS is the mean over seats of the mean CRPS of that seat\'s National and Labour candidates, arm minus control (negative favours the arm).', '']
    rows = []
    for a in order[1:]:
        c, fl = dec['comparisons'][a], dec['coverageFloor'][a]
        rows.append([LABEL[a], f(c['deltaMajorCRPSPP'], 4), pct(c['relativeDeltaMajorCRPS'], 2), f(c['deltaMajorIntervalScorePP'], 3), f(c['deltaEnergyPP'], 3),
                     f'{c["foldsNegative"]}/3', f(c['resolution']['differencePP'], 5), c['classification'], 'pass' if fl['passed'] else 'FAIL',
                     'reference' if a == 'penalised' else 'yes' if a in sel['qualifying'] else 'no'])
    out += table(['Arm', 'Delta major CRPS', 'Relative', 'Delta interval score', 'Delta energy', 'Elections improving', 'Resolution gap (16,384 vs 32,768)', 'Stage48 class', 'Coverage floor', 'Qualifies'], rows)
    best = sel['best']
    if best:
        out += [f'Among the qualifying arms the lowest pooled CRPS is **{LABEL[best]}**. Paired seat bootstrap (2,000 draws, seed 60) of each qualifier minus the best:', '']
        out += table(['Arm', '90% interval of CRPS(arm) minus CRPS(best)', 'Within noise of the best'],
                     [[LABEL[a], f'{f(v["intervalOfArmMinusBest"][0], 4)} to {f(v["intervalOfArmMinusBest"][1], 4)}', 'yes' if v['withinNoise'] else 'no']
                      for a, v in sel['withinNoise'].items()])
        out += [f'The least aggressive qualifying arm within noise of the best is **{LABEL[sel["recommended"]]}**. The descriptive alternative (least aggressive qualifier within 0.01pp of the best pooled CRPS) is {LABEL[sel["descriptiveAlternative"]]}.', '']
    out += ['## Multipliers', '',
            'The multiplier applies to the frozen Stage45 seat balance scale only. The free arm is trained on earlier elections only with the ridge removed; its 2014 value is 1 (no earlier data).', '']
    rows = []
    for y in YEARS:
        fold = fits['folds'][str(y)]
        rows.append([y, '/'.join(map(str, fold['trainingYears'])) or 'none', f(fold['multipliers']['free'], 4), f(fold['multipliers']['penalised'], 4),
                     f(fold['free']['a'], 4) if fold['trainingYears'] else '0', 'none' if not fold['trainingYears'] or not fold['free']['boundContact'] else 'yes'])
    out += table(['Target', 'Free arm trained on', 'Free multiplier', 'Stage48 K multiplier', 'Free log multiplier a', 'Bound contact'], rows)
    refit = fits['descriptive2026Refit']['fit']
    out += [f'Descriptive 2026 refit (all four elections, never scored): log multiplier {f(refit["a"], 4)}, multiplier **{f(refit["multiplier"], 4)}**. This is the value the free arm would take for the 2026 forecast.', '']
    out += ['## Scores', '', '### Pooled on the 193 decision seats (32,768 draws)', '']
    rows = []
    for a in order:
        p = S['decisionSeats'][a]
        rows.append([LABEL[a], f(p['majorCRPSPP'], 4), f(p['energyPP'], 3), *[f(p['majorIntervals'][l]['widthPP'], 2) for l in ('50', '80', '90')],
                     *[f(p['majorIntervals'][l]['coverage'], 3) for l in ('50', '80', '90')], *[f(p['majorIntervals'][l]['intervalScorePP'], 2) for l in ('50', '80', '90')]])
    out += table(['Arm', 'Major CRPS', 'Energy', 'Width 50', 'Width 80', 'Width 90', 'Coverage 50', 'Coverage 80', 'Coverage 90', 'IS 50', 'IS 80', 'IS 90'], rows)
    out += ['### Major CRPS by election', '']
    out += table(['Arm', *map(str, YEARS), 'Equal-election mean (2017-2023)'],
                 [[LABEL[a], *[f(S[str(y)][a]['majorCRPSPP'], 4) for y in YEARS], f(S['equalElectionDecision'][a]['majorCRPSPP'], 4)] for a in order])
    out += ['### Coverage by election (pooled N/L coordinates), with the coverage floor', '',
            'Floor at each election and level: min(nominal - 0.10, control coverage - 0.05). A cell below its floor is marked `*`.', '']
    rows = []
    for a in order:
        row = [LABEL[a]]
        for y in YEARS:
            for l in ('50', '80'):
                value = S[str(y)][a]['majorIntervals'][l]['coverage']
                cell = f(value, 3)
                if a in candidates and not dec['coverageFloor'][a]['rows'][f'{y}:{l}']['passed']:
                    cell += '*'
                row.append(cell)
        rows.append(row)
    thresholds = ['floor'] + [f(dec['coverageFloor']['free']['rows'][f'{y}:{l}']['threshold'], 3) for y in YEARS for l in ('50', '80')]
    out += table(['Arm', *[f'{y} @{l}' for y in YEARS for l in ('50', '80')]], rows + [thresholds])
    out += ['### Widths by election (N/L, 90% interval)', '']
    out += table(['Arm', *map(str, YEARS)], [[LABEL[a], *[f(S[str(y)][a]['majorIntervals']['90']['widthPP'], 2) for y in YEARS]] for a in order])
    out += ['## 2014, explicitly', '']
    c14 = S['2014']
    out += [f'2014 has no earlier election, so the free arm and Stage48 K equal the control there. The control already under-covers at 50% ({f(c14["control"]["majorIntervals"]["50"]["coverage"], 3)}) '
            f'while covering 80% and 90% at about nominal ({f(c14["control"]["majorIntervals"]["80"]["coverage"], 3)}, {f(c14["control"]["majorIntervals"]["90"]["coverage"], 3)}). '
            'The fixed grid arms are not trained on anything, so they can be scored there; shrinking does not help 2014:', '']
    out += table(['Arm', 'Major CRPS', 'Coverage 50', 'Coverage 80', 'Coverage 90', 'Width 90'],
                 [[LABEL[a], f(c14[a]['majorCRPSPP'], 4), *[f(c14[a]['majorIntervals'][l]['coverage'], 3) for l in ('50', '80', '90')], f(c14[a]['majorIntervals']['90']['widthPP'], 2)]
                  for a in order])
    blocked = [LABEL[a] for a in candidates if not dec['coverageFloor'][a]['passed']]
    if blocked:
        out += [f'The coverage floor blocks {", ".join(blocked)} on the 2014 80% level; its pooled score is otherwise competitive, so this floor is the binding constraint on how far the fixed grid could go.', '']
    out += ['## Composed-width implication (arithmetic, no new bank)', '',
            'Approximate National and Labour composed 90% interval widths from the Stage47 nine-seat ablation (full 29.89pp National; no candidate balance 20.84pp). "Seat only" scales only the seat part of the balance variance, which is what the arms change; "all balance" scales the whole balance variance and is an upper bound on the effect. '
            'The free arm row uses each ablation seat\'s own fold multiplier; the 2026 refit row applies the refit multiplier to every seat.', '']
    ci = dec['composedWidthImplication']
    rows = []
    for a in [*order, 'free2026Refit']:
        v = ci[a]
        name = LABEL.get(a, 'free, 2026 refit (descriptive)')
        rows.append([name, f(v['seatOnly:national']['widthPP'], 2), pct(v['seatOnly:national']['changeRelativeToControl']), f(v['allBalance:national']['widthPP'], 2),
                     pct(v['allBalance:national']['changeRelativeToControl']), f(v['seatOnly:labour']['widthPP'], 2), pct(v['seatOnly:labour']['changeRelativeToControl'])])
    out += table(['Arm', 'National 90 seat only', 'Change', 'National 90 all balance', 'Change', 'Labour 90 seat only', 'Change'], rows)
    san = dec['composedWidthSanityCheck']
    out += [f'Sanity check: the same arithmetic with Stage48 K\'s multipliers predicts a National composed 90% width change of {pct(san["arithmeticSeatOnlyChange"])} (seat only) to {pct(san["arithmeticAllBalanceChange"])} (all balance); the Stage48 composed bank (193 seats, 512 draws, precision gates unmet) shows {pct(san["stage48ComposedNationalFull90"]["change"])} '
            f'({f(san["stage48ComposedNationalFull90"]["control"], 2)} to {f(san["stage48ComposedNationalFull90"]["constant"], 2)}pp). The arithmetic is consistent in size and slightly overstates; treat the table as a rough guide, not a composed result.', '']
    out += ['## Numerical and independent checks', '']
    n = dec['numerical']
    out += table(['Arm', 'Doubling gates (8,192 to 16,384 to 32,768, representative seats)', 'mean', 'crps', 'energy', 'width50', 'width80', 'width90'],
                 [[LABEL[a], 'pass' if n['doublingAllPassed'][a] else 'FAIL', *[f(n['doublingLastChangesPP'][a][k], 4) for k in ('mean', 'crps', 'energy', 'width50', 'width80', 'width90')]] for a in order])
    e48 = ver['equalsStage48']
    out += [f'Independent checks (all passed): the control equals Stage48\'s control and the reference arm equals Stage48\'s K seat by seat on all 257 seats (maximum CRPS difference {e48["control"]["maximumAbsoluteDifference"]["crps"]:.1e} and {e48["penalised"]["maximumAbsoluteDifference"]["crps"]:.1e}, identical coverage indicators); '
            f'the free arm reproduces Stage48\'s descriptive unpenalised constant; non-balance draws and the National+Labour mass are identical across arms (maximum gap {n["maximumDrawGapAcrossArms"]:.1e}); '
            f'conditional-mean gap of every location {ver["locationChecks"]["maximumConditionalMeanGapPP"]:.1e}pp against the 0.05pp gate; pairwise-formula CRPS agrees with the vectorised score to {ver["scoreChecks"]["maximumDifferencePP"]:.1e}pp; '
            f'plain-loop pooled differences agree to {max(v["difference"] for v in ver["decisionArithmetic"].values()):.1e}; the 2014 free and reference arms are exactly the control; '
            f'all {ver["exclusion"]["seatsScored"]} scored records are general electorates (none excluded, none Māori).', '']
    free = S['decisionSeats']['free']
    ctl = S['decisionSeats']['control']
    c90, r90 = ctl['majorIntervals']['90']['widthPP'], free['majorIntervals']['90']['widthPP']
    out += ['## Reading the result', '']
    if finding.startswith('recommend_'):
        a = sel['recommended']
        r, c = S['decisionSeats'][a], dec['comparisons'][a]
        out += [f'**What the frozen test shows.** A stronger global shrink of the candidate-balance seat scale than Stage48\'s penalised K is supported. The recommended arm ({LABEL[a]}) lowers pooled N/L CRPS by {f(-c["deltaMajorCRPSPP"], 4)}pp ({pct(-c["relativeDeltaMajorCRPS"], 2)}, {f(-c["deltaMajorCRPSPP"] / -dec["comparisons"]["penalised"]["deltaMajorCRPSPP"], 1)} times Stage48 K\'s gain), '
                f'improves all three elections ({", ".join(f(-v, 4) for v in c["foldDeltaMajorCRPSPP"].values())}pp for 2017, 2020, 2023), lowers the mean N/L interval score by {f(-c["deltaMajorIntervalScorePP"], 2)} and complete-vector energy by {f(-c["deltaEnergyPP"], 3)}, and narrows the N/L candidate intervals '
                f'(50/80/90 widths {f(ctl["majorIntervals"]["50"]["widthPP"], 2)}/{f(ctl["majorIntervals"]["80"]["widthPP"], 2)}/{f(ctl["majorIntervals"]["90"]["widthPP"], 2)} to {f(r["majorIntervals"]["50"]["widthPP"], 2)}/{f(r["majorIntervals"]["80"]["widthPP"], 2)}/{f(r["majorIntervals"]["90"]["widthPP"], 2)}) '
                f'with pooled coverage still at or above nominal ({f(r["majorIntervals"]["50"]["coverage"], 3)}/{f(r["majorIntervals"]["80"]["coverage"], 3)}/{f(r["majorIntervals"]["90"]["coverage"], 3)} against {f(ctl["majorIntervals"]["50"]["coverage"], 3)}/{f(ctl["majorIntervals"]["80"]["coverage"], 3)}/{f(ctl["majorIntervals"]["90"]["coverage"], 3)}). '
                f'The gain is concentrated in 2017 and 2023; 2020 improves least ({f(-c["foldDeltaMajorCRPSPP"]["2020"], 4)}pp). The fitted multipliers are stable across folds ({", ".join(f(fits["folds"][str(y)]["multipliers"]["free"], 3) for y in (2017, 2020, 2023))}) and the all-election refit is {f(refit["multiplier"], 3)}.',
                '',
                '**The fitted and fixed arms agree.** Every qualifying arm improves every pooled criterion and the fixed grid is monotone: more shrink lowers pooled CRPS all the way to 0.80, which only the 2014 coverage floor stops. The free arm, the only one not set after seeing the likelihood-preferred size, lands in the same place as the fixed grid (0.78 to 0.85), '
                'so the leave-future-out fit and the grid agree rather than conflict.', '']
    out += ['**Where the limit is.** The shrink does not help 2014 (no arm can: the free arm has no earlier data, and the fixed grid worsens 2014 coverage at 80%), '
            f'and in 2020 the free arm leaves 50% coverage at {f(S["2020"]["free"]["majorIntervals"]["50"]["coverage"], 3)}, below nominal. Pooled 80% coverage ({f(free["majorIntervals"]["80"]["coverage"], 3)}) and 90% ({f(free["majorIntervals"]["90"]["coverage"], 3)}) are still above nominal, '
            'and the grid already shows the cost of cutting further (grid 0.80 takes 2014 80% coverage to ' + f(S['2014']['grid80']['majorIntervals']['80']['coverage'], 3) + ' and 2020 50% coverage to ' + f(S['2020']['grid80']['majorIntervals']['50']['coverage'], 3) + '); reading, not a tested claim: what remains is a distribution-shape question (Student-t was tested and rejected in Stage46), not one a smaller scale answers.', '',
            '## Limits', '',
            '- Three fitted folds from reused development elections, chronologically fitted after the fact; this is not untouched validation. The fixed grid values were chosen after Stage48 had reported the likelihood-preferred size, so grid scores are development-informed; the free arm is the only chronologically blind arm, and the 2026 result will be the first genuine out-of-sample test.',
            '- 2014 has no earlier data and is control for the free arm; the 2014 balance miss is not addressed and is made no better by any fixed shrink.',
            '- Composed 56-day precision gates remain unmet; the composed widths are arithmetic from nine ablation seats, not a bank. The 56-day horizon differs from the roughly 32-day horizon at publication; not measured here.',
            '- Parameter and scale uncertainty remain omitted; the multiplier is a point value. Only the seat balance scale moves: the shared election scale, local-party layer and national uncertainty are unchanged, so the composed 90% intervals stay wide (about ' + f(ci['free2026Refit']['allBalance:national']['widthPP'], 0) + ' to ' + f(ci['free']['seatOnly:national']['widthPP'], 0) + 'pp National).',
            '- Seat-win and winner probabilities were not evaluated; nothing here is a calibrated-probability claim.', '',
            '## Recommendation for James (not adopted)', '']
    if finding.startswith('recommend_'):
        out += ['1. **Sign-off decision.** Adopt, for the automatic output, the earlier-trained penalty-free constant, with the 2026 value set by the all-election refit '
                f'({f(refit["multiplier"], 3)} on the seat balance scale), or keep the corrected control. The scores favour adoption on every pre-registered criterion; the cost is that the default changes, which James keeps open. The stage does not flip it.',
                '2. **Treat the size as near its limit.** The coverage floor and 2014/2020 coverage argue against going below about 0.80; no further balance-scale test is needed on these data.',
                f'3. **Width implication.** This narrows the N/L candidate intervals by {pct(1 - r90 / c90, 0)} and, by arithmetic, the composed National 90% width by {pct(-ci["free"]["seatOnly:national"]["changeRelativeToControl"], 0)} to {pct(-ci["free"]["allBalance:national"]["changeRelativeToControl"], 0)} ({f(ci["free"]["seatOnly:national"]["widthPP"], 1)} to {f(ci["free"]["allBalance:national"]["widthPP"], 1)}pp from {f(ci["control"]["seatOnly:national"]["widthPP"], 1)}pp); the 2026 refit multiplier gives {pct(-ci["free2026Refit"]["seatOnly:national"]["changeRelativeToControl"], 0)} to {pct(-ci["free2026Refit"]["allBalance:national"]["changeRelativeToControl"], 0)}. Bigger gains need other layers (Stage61) or the live poll fit.', '']
    else:
        out += ['Keep the corrected control as the default; no change is recommended on this evidence.', '']
    return '\n'.join(out) + '\n'


def main():
    args = arguments()
    verify()
    text = build()
    path = ROOT / FINDINGS
    if args.check:
        if not path.exists() or path.read_text() != text:
            raise ValueError('Stale Stage60 findings document')
    else:
        path.write_text(text)


if __name__ == '__main__':
    main()
