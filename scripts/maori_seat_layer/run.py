"""Stage66 runner: transcription checks, calibration, the 2026 per-draw forecast, sensitivity arms, preview draws and manifest."""
import argparse
import numpy as np
from scripts.maori_seat_layer import verify
from scripts.maori_seat_layer.common import read, save, digest, SEATS, PREFIX, DESIGN, DESIGN_DOC, HISTORICAL_POLLS, CURRENT_POLLS, REGISTRY, ELECTION_DATES
from scripts.maori_seat_layer.fit import fit
from scripts.maori_seat_layer.simulate import current_polls, simulate, summarise

TOLERANCE = 1e-8
PREVIEW_DECIMALS = 6


def parameters(fitted, which='default'):
    base = {'sigma2': fitted['sigma2'], 'sigma2Dof': fitted['sigma2Dof'], 'tau2': fitted['tau2'], 'tauDof': 4,
            'bias': fitted['bias'], 'unnamedShares': fitted['unnamedShares']}
    if which == 'horizon':
        long = fitted['horizon']['longHorizonFit']
        return dict(base, sigma2=long['sigma2'], sigma2Dof=long['sigma2Dof'], tau2=long['tau2'], tauDof=len(long['electionsUsed']))
    if which == 'curiaEraBias':
        means = fitted['electionMeans']
        return dict(base, bias=(means['2020']['meanD'] + means['2023']['meanD']) / 2.0)
    if which == 'independentSeats':
        return dict(base, tau2=0.0)
    return base


def arms(fitted, polls, draws, seed):
    """Default arm and post-hoc sensitivity arms. Only 'default' is the model; the others are reported, never adopted."""
    specs = (('default', 'registered model', None), ('horizon', 'sigma and tau re-estimated on polls closed 21 days or more before the election (registered diagnostic)', None),
             ('curiaEraBias', 'POST HOC: constant Maori Party shift equal to the mean of the 2020 and 2023 election means of D', None),
             ('widerOtherNoise', 'POST HOC: candidates outside the Maori Party and Labour groups get log-share noise sigma_oth^2 = max(sigma^2, rms2 - sigma^2) from the registered diagnostic', 'oth'),
             ('independentSeats', 'registered default coupling check: no shared election-level shift (tau = 0)', None))
    out, default = {}, None
    other = fitted['otherContrasts']
    for name, label, extra in specs:
        which = name if name in ('horizon', 'curiaEraBias', 'independentSeats') else 'default'
        sigma_oth = max(fitted['sigma2'], other['rms2'] - fitted['sigma2']) if extra == 'oth' else None
        sim = simulate(polls, parameters(fitted, which), draws, seed, sigma_oth)
        summary = summarise(sim, draws)
        summary['description'] = label
        if name == 'default':
            default = summary
        out[name] = summary
    for name, summary in out.items():
        shifts = {}
        for seat, v in summary['seats'].items():
            shifts[seat] = max(abs(c['winProbability'] - d['winProbability']) for c, d in zip(v['candidates'], default['seats'][seat]['candidates']))
        summary['maxWinProbabilityShiftVsDefaultBySeat'] = shifts
        summary['flaggedShiftOver0.10'] = sorted(s for s, x in shifts.items() if x > 0.10) if name != 'default' else []
    return out


def preview(polls, params, draws, seed, size):
    sim = simulate(polls, params, draws, seed)
    seats = {}
    for seat, s in sim['seats'].items():
        cands = s['poll']['candidates']
        seats[seat] = {'candidates': [c['name'] for c in cands], 'parties': [c['party'] for c in cands],
                       'winnerParty': [cands[i]['party'] for i in s['winner'][:size]],
                       'winnerIndex': [int(i) for i in s['winner'][:size]],
                       'share': [[round(float(x), PREVIEW_DECIMALS) for x in row] for row in s['share'][:size]]}
    return {'schemaVersion': 1, 'label': 'PREVIEW of the first %d of %d deterministic draws; not a forecast release' % (size, draws),
            'seed': seed, 'draws': size, 'sharedFactorZ': [round(float(x), PREVIEW_DECIMALS) for x in sim['z'][:size]],
            'unpolledSeats': [s for s in SEATS if s not in polls], 'seats': seats}


def build():
    contract = read(DESIGN)
    verify_errors = verify.historical() + verify.current()
    if verify_errors:
        raise ValueError('Transcription verification failed:\n' + '\n'.join(verify_errors))
    fitted_doc, rows = fit()
    fitted = fitted_doc['fit']
    polls, superseded, data = current_polls()
    draws, seed = contract['draws'], contract['seed']
    forecast = {'schemaVersion': 1, 'label': 'INTERNAL development output; no probability release; not a forecast of record',
                'electionDate': ELECTION_DATES[2026], 'draws': draws, 'seed': seed,
                'polledSeats': sorted(polls, key=SEATS.index), 'unpolledSeats': [s for s in SEATS if s not in polls],
                'unpolledNote': 'No poll, no value: unpolled seats carry no shares or winner (missing is not zero) and no fallback is invented.',
                'supersededPollIds': superseded, 'arms': arms(fitted, polls, draws, seed),
                'parameters': {k: v for k, v in parameters(fitted).items() if k != 'unnamedShares'}}
    preview_doc = preview(polls, parameters(fitted), draws, seed, contract['previewDraws'])
    summary = {'schemaVersion': 1, 'historicalPolls': len(rows), 'contrastPolls': fitted['contrastPolls'], 'sigma': fitted['sigma'], 'tau': fitted['tau'],
               'biasAdopted': fitted['biasAdoption']['adopted'], 'biasHat': fitted['biasAdoption']['biasHat'],
               'loeoImprovementNats': fitted['biasAdoption']['loeo']['improvementNats'],
               'otherContrastRatioTo2Sigma2': fitted['otherContrasts']['ratioTo2Sigma2'],
               'backtestMeanPredictedLeaderWin': fitted['backtest']['zero']['meanPredictedLeaderWin'],
               'backtestObservedLeaderWinRate': fitted['backtest']['zero']['observedLeaderWinRate'],
               'polledSeats': forecast['polledSeats'], 'unpolledSeats': forecast['unpolledSeats'],
               'defaultWinProbabilities': {seat: {c['name']: c['winProbability'] for c in v['candidates']} for seat, v in forecast['arms']['default']['seats'].items()},
               'flaggedSensitivityShifts': {n: a['flaggedShiftOver0.10'] for n, a in forecast['arms'].items()}}
    return {'calibration-table.json': {'schemaVersion': 1, 'rows': rows}, 'calibration.json': fitted_doc, 'forecast-2026.json': forecast,
            'draw-bank-preview.json': preview_doc, 'summary.json': summary}


def manifest(names):
    inputs = [DESIGN_DOC, DESIGN, HISTORICAL_POLLS, CURRENT_POLLS, REGISTRY, PREFIX + '/historical-results.json']
    return {'schemaVersion': 1, 'inputHashes': {p: digest(p) for p in inputs}, 'dataSourcesJsonTouched': False, 'newResources': 0,
            'outputs': sorted(names)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    artifacts = build()
    for name, value in artifacts.items():
        save(name, value, args.check, TOLERANCE if name != 'draw-bank-preview.json' else 2e-6)
    save('manifest.json', manifest(list(artifacts)), args.check)
    print('Stage66 check ok' if args.check else 'wrote %d artifacts' % len(artifacts))


if __name__ == '__main__':
    main()
