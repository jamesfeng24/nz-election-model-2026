"""Frozen summary quantities computed identically for every restriction and population."""
import numpy as np
from scripts.uncertainty_expectation.audits import width_summary
from .common import RESTRICTIONS

LEVELS = (50, 80, 90)


def major_values(records, key):
    """Per-seat means over the seat's National and Labour candidates."""
    return np.array([np.mean([r[key][i] for i, g in enumerate(r['groups']) if g in ('national', 'labour')]) for r in records])


def interval_values(records, level, key):
    return [r[f'interval{level}'][key][i] for r in records for i, g in enumerate(r['groups']) if g in ('national', 'labour')]


def summarize(records):
    crps = major_values(records, 'crpsPP')
    result = {'seats': len(records),
              'majorCRPSPP': float(crps.mean()),
              'completeContestEqualCRPSPP': float(np.mean([np.mean(r['crpsPP']) for r in records])),
              'energyPP': float(np.mean([r['energyPP'] for r in records])),
              'contestEqualMAEPP': float(np.mean([r['maePP'] for r in records])),
              'majorIntervals': {}, 'forecastPair': {}}
    for level in LEVELS:
        covered = interval_values(records, level, 'covered')
        result['majorIntervals'][str(level)] = {
            'covered': int(sum(covered)), 'total': len(covered), 'coverage': float(np.mean(covered)),
            'widthPP': float(np.mean(interval_values(records, level, 'widths'))),
            'intervalScorePP': float(np.mean(interval_values(records, level, 'scores')))}
        pair = [r['ranking']['predictionTimePair'][f'interval{level}'] for r in records]
        result['forecastPair'][str(level)] = {'covered': int(sum(p['covered'][0] for p in pair)), 'total': len(pair),
            'widthPP': float(np.mean([p['widths'][0] for p in pair])), 'intervalScorePP': float(np.mean([p['scores'][0] for p in pair]))}
    result['forecastPair']['crpsPP'] = float(np.mean([r['ranking']['predictionTimePair']['crpsPP'] for r in records]))
    for group in ('national', 'labour'):
        result[group] = width_summary(records, group)
    return result


def by_population(records_by_restriction):
    """records_by_restriction: {restriction: [compact records]} for identical seats in the same order."""
    ids = [r['id'] for r in records_by_restriction['control']]
    for r in RESTRICTIONS:
        if [x['id'] for x in records_by_restriction[r]] != ids:
            raise ValueError('Unequal paired Stage48 records')
    years = sorted({r['year'] for r in records_by_restriction['control']})
    populations = {'allSeats': lambda r: True, 'fittedFolds': lambda r: r['year'] != 2014}
    for y in years:
        populations[str(y)] = (lambda y: lambda r: r['year'] == y)(y)
    result = {}
    for name, keep in populations.items():
        selected = {r: [x for x in records_by_restriction[r] if keep(x)] for r in RESTRICTIONS}
        if not selected['control']:
            continue
        result[name] = {r: summarize(selected[r]) for r in RESTRICTIONS}
    result['equalElectionFittedFolds'] = {r: {
        'majorCRPSPP': float(np.mean([result[str(y)][r]['majorCRPSPP'] for y in years if y != 2014])),
        'energyPP': float(np.mean([result[str(y)][r]['energyPP'] for y in years if y != 2014]))} for r in RESTRICTIONS}
    return result
