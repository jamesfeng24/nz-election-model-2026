"""Reproducible Stage45 findings, retaining precision and calibration failures."""
import numpy as np
from .common import PREFIX, ROOT, read, arguments


def fmt(x):
    return f'{x:.3f}'


def report():
    evaluation = read(PREFIX + '/evaluation.json')
    precision = read(PREFIX + '/convergence.json')
    audit = read(PREFIX + '/mean-audit.json')
    verification = read(PREFIX + '/independent-verification.json')
    lines = ['# Stage45 residual-scale correction findings', '',
        '2026-10-05. One post-Stage44 development correction, frozen at ed300e4 before revised scoring. Original Stage44 artifacts, mean coefficients, continuous transport, identities and operational nulls remain unchanged. No acquisition or MCMC.', '',
        '## Verified cause and single correction', '',
        'Nonmajor options account for97.05–98.43% of local squared CLR residual magnitude; coordinate count alone is not proof. Per-option heterogeneity and the direct N/L contrast verify the allocation issue: local N/L residual RMS0.1102–0.1928 versus Stage44 implied2023SD0.7650. Candidate N/L RMS0.2734–0.4036 versus old implied0.7616–0.8832. The old equations are correctly implemented. This is a statistical family limitation, not a numerical bug.', '',
        'The arithmetic tree separates raw N/L log odds, combined-major/remainder log odds and projected within-remainder intensities. Scalar balances use their own earlier-election shared/seat moments; within remainder retains all minor/independent errors with two pooled exchangeable scales. Small-category splitting cannot inflate major covariance. One-major/no-major/absent remainder mappings are explicit. Fixed1e-6 resolution replacement and frozen-zero locks remain; the consumed candidate inventory has no zero actuals, correcting loose earlier wording about nine zero-vote source occurrences.', '',
        '321party vectors and257candidate slates/1902candidates remain. Chronological uncertainty uses earlier residual years only:2011party/2014candidate are assumed priors; later estimates use1–4earlier environments. Three prior pseudo-environments strongly pool every direction. No independent coefficient/scale draws. Shared local/candidate effects are retained, national error shared once, cross-layer independence remains assumed. General coefficients/errors are not applied to Māori seats.', '',
        '## Identical-case proper-score comparison', '',
        'All values pp. Lower CRPS is better. Point is the identical frozen conditional mean, or the8000-national-draw transformed national-only mean, as a degenerate distribution. The Stage44 column is a separate unchanged-equation/scale8000-draw companion, not an overwrite of its original512-draw outputs. Contest-equal weighting and identical IDs apply.', '',
        '| Case | Seats | Coordinates | Point CRPS | Stage44 CRPS | Revised CRPS | Revised energy128 | Revised MAE | Revised RMSE |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for case in evaluation['cases']:
        s = case['methods']['revised']['summary']
        p = case['methods']['point']['summary']; old = case['methods']['unchanged_stage44']['summary']
        lines.append(f"| {case['id']} | {s['contests']} | {s['coordinates']} | {fmt(p['contestEqualCRPSPP'])} | {fmt(old['contestEqualCRPSPP'])} | {fmt(s['contestEqualCRPSPP'])} | {fmt(s['energyPP'])} | {fmt(s['contestEqualMAEPP'])} | {fmt(s['contestEqualRMSEPP'])} |")
    lines += ['', 'Revised CRPS improves over both old uncertainty and point references in all12cases. This is useful development evidence, not calibrated deployment. Local and candidate expected-share MAE remains essentially unchanged; the correction improves uncertainty allocation rather than fitting a better mean.', '',
        '## Coverage and proper interval scores', '',
        'Coordinate counts are correlated, not independent calibration observations. Full comparison records, both coverage levels, group signed bias/MAE/RMSE, proper scores, energy and substantive misses are in evaluation.json. Width/score summaries average within complete contest then contests.', '',
        '| Case | 50% covered | 50% width | 50% score | 90% covered | 90% width | 90% score |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for case in evaluation['cases']:
        s = case['methods']['revised']['summary']; a, b = s['interval50'], s['interval90']
        lines.append(f"| {case['id']} | {a['covered']}/{a['total']} | {fmt(a['contestEqualWidthPP'])} | {fmt(a['contestEqualScorePP'])} | {b['covered']}/{b['total']} | {fmt(b['contestEqualWidthPP'])} | {fmt(b['contestEqualScorePP'])} |")
    lines += ['', '### Major and remainder diagnostics', '',
        'Group errors give each selected coordinate equal weight; their averages do not sum to the whole-slate score. Major widths shrink substantially: local about9.5–12.5pp instead of28–44; candidate21–25pp instead of38–51; composed26–35pp instead of51–64. Narrowness alone is not success; CRPS and interval scores improve materially too. Some major misses now appear, including composed2017Labour53/64 andNational56/64 at90%. Pooled50% coverage remains high in many cases; calibration is not established.', '',
        '| Case | Group | Count | Revised CRPS | Stage44 CRPS | Point CRPS | Revised90% covered | Revised90% width |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for case in evaluation['cases']:
        summaries = {p: m['summary'] for p, m in case['methods'].items()}
        for group, s in summaries['revised']['groups'].items():
            old = summaries['unchanged_stage44']['groups'][group]; point = summaries['point']['groups'][group]
            lines.append(f"| {case['id']} | {group} | {s['coordinates']} | {fmt(s['crpsPP'])} | {fmt(old['crpsPP'])} | {fmt(point['crpsPP'])} | {s['interval90']['covered']}/{s['interval90']['total']} | {fmt(s['interval90']['widthPP'])} |")
    lines += ['', 'Small-option misses are retained. Other mapped candidates have slightly worse CRPS than Stage44 in candidate2020/2023 and composed2023; some minor local groups also remain worse than the point reference. No-group CRPS/coverage generally improves. All largest individual90% misses remain saved, without exclusions or adaptive scales.', '',
        '### Margins and winner diagnostics', '',
        '| Case | Mean winners | Brier | Zero actual-winner frequency | Forecast-pair CRPS | Pair90% coverage | Observed-top-two MAE |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for case in evaluation['cases']:
        s = case['methods']['revised']['summary']
        if 'ranking' not in s: continue
        r = s['ranking']
        lines.append(f"| {case['id']} | {r['uniqueMeanWinnerCorrect']}/{r['contests']} | {fmt(r['winnerBrier'])} | {r['zeroWinnerProbabilityCount']} | {fmt(r['forecastPairMarginCRPSPP'])} | {fmt(r['forecastPairMarginCoverage90'])} | {fmt(r['observedTopTwoMarginMAEPP'])} |")
    for case in evaluation['cases']:
        for r in case['methods']['revised']['records']:
            if r.get('ranking', {}).get('zeroObservedWinnerProbability'):
                lines.append(f"\nMaterial probability failure: {case['id']}/{r['name']} has zero observed-winner frequency in the finite bank, hence infinite empirical winner log loss. No probability floor is inserted. This is not a claim of mathematically zero probability under the Gaussian law.")
    lines += ['', 'Competitive pairs are chosen from prediction-time point means; observed-top-two is retrospective evaluation only. Probabilities remain diagnostics. Two or four reused environments cannot establish calibration.', '',
        '## Conditional means and common dependence', '',
        'Independent GH81 checks verify aggregate conditional arithmetic expectations versus GH41 locations within6.1e-14 shares. This preserves major mass and N/L response for each national/local input in the theoretical integration. Finite simulation means can still drift; no target outcomes adjust locations. Within remainder retains an explicitly limited weighted marginal adjustment, not conditional preservation for every national draw.', '',
        '| Case | Method | Mean absolute simulated shift pp | Maximum shift pp |',
        '| --- | --- | ---: | ---: |']
    for case in evaluation['cases']:
        for policy in ('revised', 'unchanged_stage44'):
            values = [v for r in case['meanShifts'] if r['policy'] == policy for v in r['meanShiftPP']]
            lines.append(f"| {case['id']} | {policy} | {fmt(float(np.mean(np.abs(values))))} | {fmt(float(np.max(np.abs(values))))} |")
    lines += ['', 'Composition shifts include nonlinear local-to-candidate propagation and finite integration. They are not a fitted bias correction. New average composed shifts are about0.012–0.022pp versus0.10–0.20pp for the old companion, but individual deviations remain.', '']
    for key, title in (('conditionalResponseRecords', 'Representative historical conditional-input audit'), ('syntheticConditionalResponses', 'Frozen synthetic conditional-input audit')):
        for policy in ('revised', 'unchanged_stage44'):
            rows = [r for r in audit[key] if r['policy'] == policy]
            major = max(abs(v) for r in rows for v, g in zip(r['conditionalShiftPP'], r['groups']) if g in ('national', 'labour'))
            minor = max(abs(v) for r in rows for v, g in zip(r['conditionalShiftPP'], r['groups']) if g not in ('national', 'labour'))
            lines.append(f"{title}, {policy}: maximum major conditional shift{major:.3f}pp; remainder{minor:.3f}pp. New major expectations use independently verified quadrature; old full/revised remainder audit uses fixed scrambledSobol2048, a numerical approximation.")
    lines += ['', 'The old marginal location can materially alter response at a particular national scenario; the new aggregate treatment resolves that part. Remainder conditional distortion still reaches about1.06pp on representative inputs. Shared/seat covariance contributions and cross-seat log-ratio correlations are saved in mean-audit.json; common effects have not been deleted. No additional national error, transport variance or cross-layer covariance is fitted.', '',
        '## Frozen numerical cap and precision limitations', '',
        '| Draws | Maximum mean change pp | Maximum CRPS change pp | Maximum90% width change pp | Gate |',
        '| --- | ---: | ---: | ---: | --- |']
    for r in precision['rounds']:
        c = r['changes']
        lines.append(f"| {r['draws']} | {fmt(c['meanPP']) if c else 'initial'} | {fmt(c['crpsPP']) if c else 'initial'} | {fmt(c['width90PP']) if c else 'initial'} | {'pass' if r['passed'] else 'unmet'} |")
    lines += ['', '**8000 cap reached; frozen convergence gates remain unmet.** Do not relabel this as convergence or weaken thresholds. The largest final changes0.168pp expected shares,0.189pp coordinateCRPS and1.195pp90width constrain fine differences. These are maximum representative-coordinate differences, not pooled score error bars. Both policies use the same cap/cases. Independent energy128→256 sensitivity reaches0.656pp; complete-vector energy is materially approximate. Do not use these finite checks as confidence intervals or publish excessive probability precision.', '',
        '## Decision, preservation and deployment boundary', '',
        '**Carry the revised aggregate/within implementation forward for development simulations, preserving Stage44 as a control.** Its cause-based correction yields materially sharper proper scores while retaining minor errors and cross-seat dependence. No mean-model or national-engine preference changes. This is not an operational uncertainty/calibration approval: earliest priors, few repeatedly inspected elections, conditional minor distortions, numerical cap failure, zero-frequency winner miss and omitted parameter/scale uncertainty remain consequential.', '',
        'Complete dated nominations, separately designed Māori baseline/electorate polls, all-population reconciliation/turnout, fine Other allocation and fragment composition, then MMP/live assembly remain separately bounded. No new family search, acquisition, nomination refresh or inference starts automatically.', '',
        '## Reproduction and validation', '',
        'Run diagnosis, priors, estimation, construction, evaluation, mean_audit, verification, report, manifest as `.venv/bin/python -m scripts.uncertainty_revision.NAME --check`. Construction caches exact-signature NPZ files under `.cache/stage45/`; local commits preserve resumable state. No MCMC. Cache bytes match their runtime SHA; cross-platform metadata/draw comparisons retain1e-10 tolerance. Finite dot products use explicit sum/einsum to avoid platform floating-status warnings without changing equations.', '',
        'Independent scalar/QR scales, GH81 expectations, simplex vectors, CDF-integralCRPS, quantiles/interval scores, energy, winner and all paired/group/pooled arithmetic are separately recorded. Full local/configured checks and final-head Ubuntu status are recorded in PROJECT_STATE and the PR handoff. Prior1774datafiles and consumed code/coefficients/identities remain unchanged.', '',
        '## Bounded CI cost control', '',
        'Hosted CI previously ran on all pushes plus PR events. It now runs on PR events and main pushes, with workflow/event/PR-or-ref concurrency. Local resumable commits replace routine checkpoint pushes; unskipped remote PR updates still trigger runs. Optional non-review backups may use skip markers, leaving required checks pending; final review and merge heads must be unskipped. No marker in PR title/default merge message, no protection/check removal.', '',
        'The first restructured review head and main retain complete Ubuntu verification. Conservative dependency-aware reuse and semantic archival-test details are in docs/ci-validation.md; hash integrity is not independent Linux reproduction. No extra hosted benchmarking, generated-output caching or scheduled workflow. Savings are duplicate and routine archival-work avoidance, not a guaranteed minute allowance.'
    ]
    return '\n'.join(lines) + '\n'


def main():
    args = arguments(); text = report(); path = ROOT / 'docs/stage45-uncertainty-findings.md'
    if args.check:
        if path.read_text() != text: raise ValueError('Stale Stage45 findings')
    else: path.write_text(text)
    print('Stage45 findings reproduced')


if __name__ == '__main__':
    main()
