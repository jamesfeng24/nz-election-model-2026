"""Candidate balance observations, frozen means, fold scales and forecast-time features."""
import numpy as np
from scripts.uncertainty.construction import scale_for
from scripts.uncertainty_revision.coordinates import coordinates, partition
from .common import INVENTORY, SCALES, STRUCTURE, HETEROGENEITY, read, design

YEARS = (2014, 2017, 2020, 2023)


def environments():
    """Per-year arrays; features are outcome-free, `v` is the actual balance observation."""
    inventory, scales = read(INVENTORY), read(SCALES)
    structure = {r['id']: r for r in read(STRUCTURE)['structuralRecords']}
    supported = {r['id']: r for r in read(HETEROGENEITY)['records']}
    result = {}
    for year in YEARS:
        rows = [r for r in inventory['candidateRecords'] if r['targetYear'] == year]
        fit = scale_for(scales, 'candidate', year)['scales']['balance']
        p, v, xr, xt, flags, ids = [], [], [], [], [], []
        for row in rows:
            n, l, _ = partition(row['groups'])
            major = row['mean'][n[0]] + row['mean'][l[0]]
            ratio = row['mean'][n[0]] / major
            observed = coordinates(row['actual'], row['groups'])['balance']
            if not 0 < ratio < 1 or observed is None:
                raise ValueError('Stage48 requires a defined interior balance: ' + row['targetElectorateId'])
            cid = row['targetElectorateId']
            r_value, t_value = supported[cid]['supportedR'], structure[cid]['sourceNonmajorSupportProxy']
            flags.append({'R': r_value is None, 'T': t_value is None})
            p.append(ratio); v.append(float(observed)); ids.append(cid)
            xr.append(np.nan if r_value is None else 1. - r_value)
            xt.append(np.nan if t_value is None else float(t_value))
        result[year] = {'ids': ids, 'p': np.array(p), 'v': np.array(v), 'xR': np.array(xr), 'xT': np.array(xt),
                        'seat': float(fit['seat']), 'shared': float(fit['shared']), 'missing': flags}
    return result


def centers(env, years):
    """Equal-election/equal-seat training means; target outcomes never enter."""
    if not years:
        return {'R': 0., 'T': 0.}
    return {'R': float(np.mean([np.nanmean(env[y]['xR']) for y in years])),
            'T': float(np.mean([np.nanmean(env[y]['xT']) for y in years]))}


def centered(env, year, center):
    """Centred features; a missing value is neutral (0) and flagged, never a known zero."""
    return np.column_stack((np.nan_to_num(env[year]['xR'] - center['R'], nan=0.),
                            np.nan_to_num(env[year]['xT'] - center['T'], nan=0.)))


def folds():
    return {int(k): v for k, v in design()['folds'].items()}
