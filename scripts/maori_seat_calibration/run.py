"""Stage71 runner: chronological and leave-one-election-out scoring of C, P and PB, the frozen finding rule, the 2026 readout and the manifest."""
import argparse
import numpy as np
from scripts.maori_seat_layer.data import calibration_rows
from scripts.maori_seat_layer.common import SEATS
from scripts.maori_seat_layer.simulate import current_polls
from scripts.maori_seat_calibration import model, score, readout
from scripts.maori_seat_calibration.common import read, save, digest, DESIGN, DESIGN_DOC, PREFIX, STAGE66

CURRENT_ARMS = ('C', 'P', 'PBera')


def subset(recs, years):
    return [r for r in recs if r['year'] in years]


def scheme_results(rows, scheme, contract, draws, replicates):
    fits, records = score.score_scheme(rows, scheme, draws, replicates, contract['seed'], contract['winnerLogScoreFloor'])
    folds = sorted(fits)
    out = {'foldsScored': folds, 'fits': {str(e): f for e, f in fits.items()}, 'pollRecords': records, 'pooled': {}, 'byFold': {}, 'comparisons': {}}
    for arm, recs in records.items():
        out['pooled'][arm] = score.metrics(recs)
        out['byFold'][arm] = {str(e): score.metrics(subset(recs, {e})) for e in folds}
    for a, b in (('C', 'P'), ('P', 'PB'), ('C', 'PB')):
        out['comparisons'][a + '->' + b] = score.paired_bootstrap(records[a], records[b], contract['pairedPollBootstrapResamples'], contract['seed'])
    return out


def finding(rows, scheme_out, years, contract, label):
    """Apply the frozen rule to P against C on a set of held-out elections."""
    recs = {a: subset(scheme_out['pollRecords'][a], years) for a in score.ARMS}
    folds = [e for e in scheme_out['foldsScored'] if e in years]
    c, p = score.metrics(recs['C']), score.metrics(recs['P'])
    fold_c = {e: score.metrics(subset(recs['C'], {e})) for e in folds}
    fold_p = {e: score.metrics(subset(recs['P'], {e})) for e in folds}
    fits = {e: scheme_out['fits'][str(e)] for e in folds}
    cls = score.classify(c, p, fold_c, fold_p, fits, contract['bootstrapMaxSkipFraction'], contract['calibrationZThreshold'], contract['minimumFoldsBrierBetter'])
    cmp = score.paired_bootstrap(recs['C'], recs['P'], contract['pairedPollBootstrapResamples'], contract['seed'])
    qualifier = None
    if cls == 'restored':
        qualifier = 'clear' if cmp['brierInterval90'][1] < 0 else 'weak'
    pb = score.metrics(recs['PB'])
    pbcmp = score.paired_bootstrap(recs['P'], recs['PB'], contract['pairedPollBootstrapResamples'], contract['seed'])
    testable = [e for e in (2017, 2023) if e in folds]
    fold_pb = {e: score.metrics(subset(recs['PB'], {e})) for e in testable}
    fold_p_t = {e: fold_p[e] for e in testable}
    pb_ok = (pb['brierLeader'] < p['brierLeader'] and pb['meanLogScoreWinner'] > p['meanLogScoreWinner']
             and all(fold_pb[e]['brierLeader'] <= fold_p_t[e]['brierLeader'] and fold_pb[e]['meanLogScoreWinner'] >= fold_p_t[e]['meanLogScoreWinner'] for e in testable))
    return {'scheme': label, 'heldOutElections': folds, 'polls': c['polls'], 'finding': cls, 'evidenceQualifier': qualifier,
            'control': c, 'inflation': p, 'inflationVsControl': cmp, 'foldBrierControl': {str(e): fold_c[e]['brierLeader'] for e in folds},
            'foldBrierInflation': {str(e): fold_p[e]['brierLeader'] for e in folds},
            'eraBiasVsInflation': {'pooled': pbcmp, 'metrics': pb, 'testableFolds': testable, 'finding': 'suggestive_not_adopted' if pb_ok else 'not_supported'}}


def readout_2026(rows, contract, polls):
    draws, seed, stage66_seed = contract['draws'], contract['seed'], read(STAGE66 + '/design-contract.json')['seed']
    units = model.units_from_rows(rows, sorted({r['year'] for r in rows}))
    unnamed = sorted(r['unnamedShare'] for r in rows)
    fits = {a: model.fit_arm(units, a == 'PBera') for a in ('C', 'PBera')}
    boot = {}
    for a in ('P', 'PBera'):
        rng = np.random.default_rng(np.random.SeedSequence([seed, 2026, 1 if a == 'P' else 2]))
        lam, skipped = model.bootstrap(units, a == 'PBera', contract['bootstrapReplicates'], rng)
        boot[a] = {'lambda': lam, 'skipped': skipped, 'interval': model.interval(lam)}
    est_c, est_b = fits['C'], fits['PBera']
    curia_bias = model.era_bias_for(units, 'Curia')
    lam_hat = est_c['lambdaHat']
    iv = boot['P']['interval']
    rng_l = np.random.default_rng(np.random.SeedSequence([seed, 2026, 3]))
    arms = {
        'C': (est_c, 1.0, 0.0, 'Stage66 unchanged'),
        'P': (est_c, boot['P']['lambda'][rng_l.integers(0, len(boot['P']['lambda']), draws)], 0.0, 'variance inflation, lambda drawn from the bootstrap of the correction'),
        'P_lambda_hat': (est_c, lam_hat, 0.0, 'variance inflation fixed at the fitted lambda'),
        'P_lambda_p05': (est_c, iv['p05'], 0.0, 'variance inflation fixed at the 5th percentile of the bootstrap'),
        'P_lambda_p95': (est_c, iv['p95'], 0.0, 'variance inflation fixed at the 95th percentile of the bootstrap'),
        'PB': (est_b, boot['PBera']['lambda'][np.random.default_rng(np.random.SeedSequence([seed, 2026, 4])).integers(0, len(boot['PBera']['lambda']), draws)], curia_bias,
               'inflation plus Curia-era bias for the Maori Party candidates (mean of the 2020 and 2023 election means of D)')}
    out, control = {}, None
    for name, (est, lam, bias, label) in arms.items():
        sim = readout.simulate(polls, est, lam, bias, unnamed, stage66_seed, draws)
        summary = readout.describe(sim, draws, control)
        summary['description'] = label
        if name == 'C':
            control = summary
        out[name] = summary
    all_fit = {'sigma2': est_c['sigma2'], 'sigma2Dof': est_c['sigma2Dof'], 'tau2': est_c['tau2'], 'lambdaHat': lam_hat,
               'lambdaInterval90': {'p05': iv['p05'], 'p50': iv['p50'], 'p95': iv['p95']}, 'bootstrapSkipped': boot['P']['skipped'],
               'eraBias': {'Curia': curia_bias, 'tau2WithEraBias': est_b['tau2'], 'lambdaHatWithEraBias': est_b['lambdaHat'], 'lambdaIntervalWithEraBias90': boot['PBera']['interval'],
                           'bootstrapSkipped': boot['PBera']['skipped']}}
    return {'schemaVersion': 1, 'label': 'INTERNAL development output; nothing adopted; not a forecast of record', 'draws': draws, 'seed': stage66_seed, 'bootstrapSeed': seed,
            'polledSeats': sorted(polls, key=SEATS.index), 'fitAllFourElections': all_fit, 'arms': out}


def build():
    contract = read(DESIGN)
    rows = calibration_rows()
    polls, _, _ = current_polls()
    draws, reps = contract['draws'], contract['bootstrapReplicates']
    chrono = scheme_results(rows, 'chronological', contract, draws, reps)
    loeo = scheme_results(rows, 'leaveOneElectionOut', contract, draws, reps)
    findings = {'schemaVersion': 1, 'headline': finding(rows, chrono, {2017, 2020, 2023}, contract, 'chronological 2017, 2020, 2023'),
                'robustness': {'chronological2020And2023': finding(rows, chrono, {2020, 2023}, contract, 'chronological 2020, 2023'),
                               'leaveOneElectionOut': finding(rows, loeo, {2014, 2017, 2020, 2023}, contract, 'leave one election out')}}
    repro = score.reproduce_stage66_control(rows, read(STAGE66 + '/design-contract.json')['seed'], 20000, contract['winnerLogScoreFloor'])
    stored = read(STAGE66 + '/calibration.json')['fit']['backtest']['zero']
    gap = max(abs(repro[k] - stored[k]) for k in repro)
    if gap > 1e-9:
        raise ValueError('Arm C no longer reproduces the stored Stage66 backtest (max gap %g)' % gap)
    scores = {'schemaVersion': 1, 'stage66Reproduction': {'draws': 20000, 'seed': read(STAGE66 + '/design-contract.json')['seed'], 'control': repro, 'stored': {k: stored[k] for k in repro}, 'maxAbsoluteGap': gap},
              'chronological': chrono, 'leaveOneElectionOut': loeo}
    forecast = readout_2026(rows, contract, polls)
    summary = {'schemaVersion': 1, 'headlineFinding': findings['headline']['finding'], 'headlineQualifier': findings['headline']['evidenceQualifier'],
               'robustnessFindings': {k: v['finding'] for k, v in findings['robustness'].items()},
               'lambdaHatAllFourElections': forecast['fitAllFourElections']['lambdaHat'], 'lambdaInterval90': forecast['fitAllFourElections']['lambdaInterval90'],
               'chronologicalPooled': chrono['pooled'], 'leaveOneElectionOutPooled': loeo['pooled'],
               'winProbabilities2026': {a: {s: {c['name']: c['winProbability'] for c in v['candidates']} for s, v in arm['seats'].items()} for a, arm in forecast['arms'].items()},
               'flaggedShifts2026': {a: arm.get('flaggedShiftOver0.10', []) for a, arm in forecast['arms'].items()}}
    return {'scores.json': scores, 'findings.json': findings, 'forecast-2026.json': forecast, 'summary.json': summary}


def manifest(names):
    inputs = [DESIGN_DOC, DESIGN, 'data/source-plans/maori-seat-layer/historical-polls.json', 'data/source-plans/maori-seat-layer/polls-2026.json',
              STAGE66 + '/historical-results.json', STAGE66 + '/calibration.json', STAGE66 + '/forecast-2026.json']
    return {'schemaVersion': 1, 'inputHashes': {p: digest(p) for p in inputs}, 'stage66Modified': False, 'dataSourcesJsonTouched': False, 'newResources': 0, 'outputs': sorted(names)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    artifacts = build()
    for name, value in artifacts.items():
        save(name, value, args.check)
    save('manifest.json', manifest(list(artifacts)), args.check)
    print('Stage71 check ok' if args.check else 'wrote %d artifacts' % len(artifacts))


if __name__ == '__main__':
    main()
