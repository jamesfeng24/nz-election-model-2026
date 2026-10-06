"""Frozen summary quantities for the lean National/Labour records, identical for every arm and population."""
import numpy as np
from .common import YEARS, LEVELS, arms


def summarize(records):
    crps = np.array([np.mean(r['crpsPP']) for r in records])
    out = {'seats': len(records), 'majorCRPSPP': float(crps.mean()), 'energyPP': float(np.mean([r['energyPP'] for r in records])),
           'meanMultiplier': float(np.mean([r['multiplier'] for r in records])), 'majorIntervals': {}}
    for level in LEVELS:
        flat = lambda key: [v for r in records for v in r['intervals'][str(level)][key]]
        covered = flat('covered')
        out['majorIntervals'][str(level)] = {'covered': int(sum(covered)), 'total': len(covered), 'coverage': float(np.mean(covered)),
                                              'widthPP': float(np.mean(flat('widths'))), 'intervalScorePP': float(np.mean(flat('scores')))}
    return out


def by_population(records):
    """records: {arm: [lean records]} for identical seats in the same order."""
    order = arms()
    ids = [r['id'] for r in records['control']]
    for a in order:
        if [r['id'] for r in records[a]] != ids:
            raise ValueError('Unequal paired Stage60 records')
    populations = {'allSeats': lambda r: True, 'decisionSeats': lambda r: r['year'] != 2014}
    populations.update({str(y): (lambda y: lambda r: r['year'] == y)(y) for y in YEARS})
    result = {}
    for name, keep in populations.items():
        result[name] = {a: summarize([r for r in records[a] if keep(r)]) for a in order}
    result['equalElectionDecision'] = {a: {'majorCRPSPP': float(np.mean([result[str(y)][a]['majorCRPSPP'] for y in YEARS if y != 2014]))}
                                       for a in order}
    return result
