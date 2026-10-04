"""Deterministic national-only findings from archived inference and scores."""
import argparse
from .common import ROOT,OUT,read


def number(value):
    return '—' if value is None else f'{value:.4f}'


def point_table(cases):
    lines=['| Case | Model status | Model MAE | Average MAE | Model RMSE | Average RMSE | MAE gain |',
           '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for r in cases:
        c=r['coarseComparison'] or {};b=r['benchmark'] or {};m=r['model']['coarsePoint'] if r['model'] else {}
        lines.append(f"| {r['year']} / {r['horizonDays']}d | {r['status']} | {number(m.get('MAEpp'))} | {number(b.get('MAEpp'))} | {number(m.get('RMSEpp'))} | {number(b.get('RMSEpp'))} | {number(c.get('MAEImprovementPP'))} |")
    return lines


def uncertainty_table(cases):
    lines=['| Case | CRPS | Energy | 50% coverage | 90% coverage | 50% width | 90% width |',
           '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in cases:
        p=r['model']['coarseProbability'] if r['model'] else {}
        lines.append(f"| {r['year']} / {r['horizonDays']}d | {number(p.get('meanCRPSpp'))} | {number(p.get('energyScorePP'))} | {number(p.get('coverage50'))} | {number(p.get('coverage90'))} | {number(p.get('width50PP'))} | {number(p.get('width90PP'))} |")
    return lines


def party_table(pool):
    lines=['| Category | Cases | Model MAE | Average MAE | Model bias | Average bias |',
           '| --- | ---: | ---: | ---: | ---: | ---: |']
    for p in pool.get('partyMetrics',[]):
        lines.append(f"| {p['category']} | {p['caseCount']} | {number(p['modelMAEpp'])} | {number(p['benchmarkMAEpp'])} | {number(p['modelBiasPP'])} | {number(p['benchmarkBiasPP'])} |")
    return lines


def numerical_table(index):
    lines=['| Saved case | Attempt | Status | Seconds | Max R-hat | Min bulk / tail ESS | Divergences | Depth contacts |',
           '| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |'];seen=set()
    for case in index:
        for path in case.get('attempts',[]):
            if path in seen:continue
            seen.add(path);a=read(OUT/path);d=a.get('diagnostics',{})
            lines.append(f"| {a.get('sourceCaseId',case['id'])} | {a['attempt']} | {a['status']} | {number(a.get('runtimeSeconds'))} | {number(d.get('maxRhat'))} | {number(d.get('minBulkESS'))} / {number(d.get('minTailESS'))} | {d.get('divergences','unavailable')} | {d.get('treeDepthContacts','unavailable')} |")
    return lines


def text_report():
    result=read(OUT/'evaluation.json');index=read(OUT/'construction.json')['cases'];verification=read(OUT/'independent-verification.json')
    lines=['# Stage36 national poll-of-polls backtest', '',
           'National-only chronological research under Stage35/D068. Election-day forecasts are scored; current latent support is reported separately and is not directly validated against the later result. Candidate components and operational selections are unchanged.', '',
           '## Primary findings', '',
           'All share/error/width/CRPS/energy quantities below are percentage points. Positive MAE gain means the model beats the average. Seven common categories include TOP within Other; eight-category fine results retain TOP separately from 2017 onward. Complete per-party errors, intervals, uncertainty covariances and diagnostics are in `evaluation.json`.', '']
    primary=[r for r in result['cases'] if r['branch']=='primary'];lines+=point_table(primary)
    lines+=['', '### Uncertainty', '']+uncertainty_table(primary)
    lines+=['', '### Major-party and small-party accounting', '',
            'Each category below receives equal case weight (four elections, two horizons each). Overall signed bias cancels on the complete simplex; party bias is informative. Many small categories must not conceal National/Labour errors.', '']
    primary_pool=next(p for p in result['pooled'] if p['branch']=='primary');lines+=party_table(primary_pool)
    lines+=['', '## Finite sensitivities and coverage', '',
            'Primary uses verified publication plus the declared five-day inference. Timing sensitivity substitutes ten days; missing-n sensitivity substitutes 1,000 for 750 in the model only. Verified-only never silently promotes inferred dates. No sensitivity Cartesian product or score-guided adjustment.', '',
            '| Branch | Model / 8 | Average / 8 | Common | Model MAE | Average MAE | MAE gain | Model RMSE | Average RMSE |',
            '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for p in result['pooled']:
        lines.append(f"| {p['branch']} | {p['modelCases']} | {p['benchmarkCases']} | {p['commonCases']} | {number(p.get('modelMAEpp'))} | {number(p.get('benchmarkMAEpp'))} | {number(p.get('MAEImprovementPP'))} | {number(p.get('modelRMSEpp'))} | {number(p.get('benchmarkRMSEpp'))} |")
    lines+=['', 'Full pools require eight cases. Incomplete available-only pools renormalize the frozen 1/8 case weights and are labelled accordingly; they are not equivalent to complete coverage. Pooled RMSE takes the square root after pooling squared errors, never averages fold RMSEs.', '']
    for branch in ('publication_lag10','missing_n1000','verified_only'):
        lines+=['### '+branch,'']+point_table([r for r in result['cases'] if r['branch']==branch])+['']
    lines+=['## Numerical attempts', '',
            'All relevant sampled paths, initial states, house/method effects, cycle biases and election-day outputs are checked coordinate by coordinate. The frozen gates are rank R-hat ≤1.01, bulk/tail ESS ≥400 and no divergences. Exact constants are identified separately. Failed first attempts remain saved; only the frozen retry was allowed. Depth contacts and BFMI remain visible. Identical complete signatures reuse the same fit, not a fresh run.', '']+numerical_table(index)
    lines+=['', '## Independent verification and preservation', '',
            f"Independent arithmetic checked {verification['benchmarkPollVectors']} poll projections, {verification['benchmarkCaseMeans']} average vectors, {verification['representativeTransformedDraws']} paired transformed draws, {verification['posteriorMeanVectors']} expected-share vectors, {verification['pointMetrics']} point/pooling checks and {verification['probabilityMetrics']} probability/interval/aggregation checks. All {verification['priorFilesPreserved']} earlier data artifacts remain byte-identical.", '',
            'The check uses independent constrained SLSQP projections, scalar Helmert/exp calculations and compensated summation, prefix-pair CRPS, manual linear quantiles and SciPy pair distances. Routine CI verifies saved outputs without historical MCMC; isolated local synthetic tests validate likelihoods/gradients and a four-chain smoke run. Neither the smoke run nor saved-output reproduction establishes empirical calibration.', '',
            '## Interpretation and boundaries', '',
            '- Four reused election environments and two dependent horizons per election provide limited calibration evidence. Poll count is not election replication.',
            '- Publication timing is mostly inferred; current source snapshots are not proven archived as-of releases. Five-/ten-day assumptions and verified-only coverage are explicit.',
            '- The first holdout has no earlier completed polling-cycle anchor to estimate common error; its uncertainty is especially prior-driven. Reported hyperparameter summaries are not proof of calibration.',
            '- Gaussian interval observations are conditionally independent approximations, not multinomial ballots. Nominal n and assumed decided fractions are not measured effective sample sizes.',
            '- Future diffusion is additional to current-state uncertainty; common polling error is already in the latent posterior and must not be drawn a second time downstream.',
            '- NumPy emitted floating-status matmul warnings after JAX. Finite/conservation checks and independent scalar reconstructions verify the saved values; no equation or tolerance was altered to suppress warnings.',
            '- A pre-score source audit corrected three distinct benchmark waves (15 case instances) to obey supported coarse-Other lower rounding bounds. The original unconstrained-remainder checkpoint is retained. No MCMC inputs or historical target errors informed this correction.',
            '- Fine-party allocation within Other remains unavailable. Joint national draws cannot yet feed a complete candidate replay without a separately authorized allocation/interface decision.',
            '- No candidate replay, national variants, live2026 output or operational choice follows. S/S+R stay active, R challenger and baseline control.', '',
            '## Reproduction and resume', '',
            'Install `requirements-polling.lock` in the isolated `.venv-polling`; retain the recorded runtime/environment. `MPLCONFIGDIR=/tmp/stage36-matplotlib .venv-polling/bin/python -m scripts.polling.national_model.inference` resumes all registered cases using exact signatures. Bounded queue wrappers keep private indexes and share exact fit archives. Never rerun completed MCMC for tables.', '',
            'After forecast archival: run `archive --check`, `evaluation --check`, `verification --check`, and `report --check` under `scripts.polling.national_model`. Deterministic readers use the original project environment; no inference dependency installation is required in routine CI.', '']
    return '\n'.join(lines)


def run(check=False):
    path=ROOT/'docs/stage36-national-polling-results.md';text=text_report()
    if check:
        if path.read_text()!=text:raise ValueError('Changed national report')
    else:path.write_text(text)
    print('National-only report deterministic; no inference')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
