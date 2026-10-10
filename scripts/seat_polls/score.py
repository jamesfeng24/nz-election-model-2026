"""Stage79 leave-one-seat-election-out scoring of the poll update against the model alone (Gaussian on the balance scale)."""
import numpy as np
from . import model
from .common import parameters

LEVELS = (50, 80, 90)


def fitted_inflation(units, held_out, design, fixed_one=False):
    """c fitted on every other seat-election's polls in `units` (each has an error y - actual and a sampling variance)."""
    if fixed_one:
        return 1.0
    pool = [u for u in units if u['seatElection'] != held_out]
    return model.fit_inflation([u['value'] - u['actual'] for u in pool], [u['samplingVariance'] for u in pool])


def score_poll(u, c, design):
    update, error = design['update'], design['pollError']
    allowance = error['allowance'].get(u['sponsorGroup'], error['allowance']['all other groups'])
    variance = c * u['samplingVariance'] + allowance ** 2
    centre, var, w = model.update(u['centre'], u['sigma2'], u['sharedVariance'], u['value'], variance, 1.0, parameters(design)['cap'])
    z = u['actual']
    return {'id': u['id'], 'seatElection': u['seatElection'], 'exceptional': u['exceptional'], 'sampleSizeAssumed': u['sampleSizeAssumed'],
            'pollValue': u['value'], 'actual': z, 'modelCentre': u['centre'], 'modelSD': u['sigma2'] ** 0.5,
            'inflation': c, 'pollSD': variance ** 0.5, 'weight': w, 'posteriorCentre': centre, 'posteriorSD': var ** 0.5,
            'logScoreModel': model.log_density(z, u['centre'], u['sigma2']), 'logScoreModelPlusPoll': model.log_density(z, centre, var),
            'crpsModel': model.crps(z, u['centre'], u['sigma2']), 'crpsModelPlusPoll': model.crps(z, centre, var),
            'covered': {str(l): {'model': bool(model.interval_covered(z, u['centre'], u['sigma2'], l)),
                                 'modelPlusPoll': bool(model.interval_covered(z, centre, var, l))} for l in LEVELS},
            'pollLeaderWon': None}


def run_arm(units, calibration_units, design, fixed_one=False, drop_assumed=False):
    """Score the eligible polls in `units`; c is fitted on `calibration_units` excluding the held-out seat-election."""
    if drop_assumed:
        units = [u for u in units if not u['sampleSizeAssumed']]
        calibration_units = [u for u in calibration_units if not u['sampleSizeAssumed']]
    records = [score_poll(u, fitted_inflation(calibration_units, u['seatElection'], design, fixed_one), design) for u in units]
    gain = sum(r['logScoreModelPlusPoll'] - r['logScoreModel'] for r in records)
    n = len(records)
    coverage = {str(l): {a: sum(r['covered'][str(l)][a] for r in records) / n for a in ('model', 'modelPlusPoll')} for l in LEVELS}
    return {'polls': n, 'seatElections': len({r['seatElection'] for r in records}), 'records': records,
            'totalLogScoreGain': gain, 'meanLogScoreGain': gain / n,
            'meanCRPS': {'model': float(np.mean([r['crpsModel'] for r in records])), 'modelPlusPoll': float(np.mean([r['crpsModelPlusPoll'] for r in records]))},
            'coverage': coverage,
            'improved': sum(r['logScoreModelPlusPoll'] > r['logScoreModel'] for r in records),
            'worsened': sum(r['logScoreModelPlusPoll'] < r['logScoreModel'] for r in records),
            'inflationRange': [min(r['inflation'] for r in records), max(r['inflation'] for r in records)]}


def decide(arm, design):
    rule, p = design['scoring']['adoptionRule'], parameters(design)
    gain_ok = arm['totalLogScoreGain'] >= p['gainNats']
    low, high = p['coverageBand']
    cover = arm['coverage']['80']['modelPlusPoll']
    cover_ok = low <= cover <= high
    return {'totalLogScoreGain': arm['totalLogScoreGain'], 'gainThresholdNats': p['gainNats'], 'gainMet': bool(gain_ok),
            'coverage80ModelPlusPoll': cover, 'coverageBand': [low, high], 'coverageMet': bool(cover_ok),
            'finding': 'adopt' if gain_ok and cover_ok else 'not_established', 'ruleText': rule['adopt']}
