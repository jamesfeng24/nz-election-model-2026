"""Stage79 historical scoring inputs: polls joined to the Stage44 out-of-sample seat replay.

DEVELOPMENT DIAGNOSTIC ONLY. The historical multiplier class comes from the Stage67 primary flags (human judgement on 2014-2023,
keyed by seat name), which D107 forbids the live build to read. Only the scoring runner imports this module; the live path
(live.py, apply.py, readout.py, the assembly) never does, and a test enforces that.
"""
import numpy as np
from scripts.uncertainty.construction import scale_for
from scripts.uncertainty_revision.coordinates import partition, mean_logit_location
from .common import INVENTORY, SCALES, read, fold
from .data import polls, derived

FLAGS = 'data/processed/exceptional-balance-scale/evaluation.json'


def historical_units(design):
    """Polls with a Stage44 out-of-sample seat replay (2014-2023), with the model reference and the actual balance."""
    inventory = [r for r in read(INVENTORY)['candidateRecords'] if r['scope'] == 'general']
    scales = read(SCALES)
    exceptional = {r['id']: r['exceptional'] for r in read(FLAGS)['records']['control']}
    multipliers = design['quantity']['multiplier']
    units = []
    for p in polls():
        if p['election'] == 2026:
            continue
        d = derived(p, design)
        if not d['hasNationalAndLabour']:
            continue
        match = [r for r in inventory if r['targetYear'] == p['election'] and fold(r['name']) == fold(p['electorate'])]
        if len(match) != 1:
            d['status'] = 'no_replay_record'
            units.append(d)
            continue
        r = match[0]
        n, l, _ = partition(r['groups'])
        mean, actual = np.asarray(r['mean']), np.asarray(r['actual'])
        balance = scale_for(scales, 'candidate', p['election'])['scales']['balance']
        multiplier = multipliers['exceptional' if exceptional[r['targetElectorateId']] else 'ordinary']
        shared2, seat2 = balance['shared'] ** 2, (balance['seat'] * multiplier) ** 2
        sigma2 = shared2 + seat2
        centre = float(mean_logit_location(np.array([mean[n[0]] / (mean[n[0]] + mean[l[0]])]), sigma2 ** 0.5)[0])
        d.update({'status': 'ok', 'seatId': r['targetElectorateId'], 'exceptional': bool(exceptional[r['targetElectorateId']]),
                  'multiplier': multiplier, 'sharedVariance': shared2, 'sigma2': sigma2, 'centre': centre,
                  'actual': float(np.log(actual[n[0]] / actual[l[0]])), 'seatElection': f"{p['election']}:{p['electorate']}"})
        units.append(d)
    return units
