"""Voting-place allocation of 2023 general-electorate votes to the 2025 general electorates.

Everything here is per old seat: place flows, population flows and the convex mixture for non-place votes all sum to one over
the old seat's target seats, so each old-seat total is conserved exactly. Pure numpy/scipy; no I/O.
"""
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Point


def seat_frames(rows):
    """source code -> arrays for the meshblocks of that 2020 seat (target index, population, bounds, centroid)."""
    grouped = {}
    for row in rows:
        grouped.setdefault(row['source'], []).append(row)
    seats = {}
    for source, items in grouped.items():
        targets = sorted({r['target'] for r in items})
        index = {t: k for k, t in enumerate(targets)}
        population = np.array([r['population'] for r in items], dtype=float)
        suppressed = np.array([r['suppressed'] for r in items], dtype=bool)
        lower = np.where(suppressed, 0.0, np.maximum(6.0, population - 2.0))
        upper = np.where(suppressed, 5.0, population + 2.0)
        seats[source] = {'targets': targets, 'tindex': np.array([index[r['target']] for r in items]),
                         'population': population, 'lower': lower, 'upper': upper,
                         'xy': np.array([[r['x'], r['y']] for r in items])}
    return seats


def population_flow(seat, population=None):
    """a_j: share of the old seat's electoral population in each target seat."""
    pop = seat['population'] if population is None else population
    total = np.bincount(seat['tindex'], weights=pop, minlength=len(seat['targets']))
    return total / total.sum()


def nearest_flows(seat, site_xy, population=None):
    """Flow matrix F [S x T] by nearest-site catchments, and a mask of sites whose catchment holds no population."""
    pop = seat['population'] if population is None else population
    tree = cKDTree(site_xy)
    _, nearest = tree.query(seat['xy'])
    s, t = len(site_xy), len(seat['targets'])
    mass = np.zeros((s, t))
    np.add.at(mass, (nearest, seat['tindex']), pop)
    row = mass.sum(axis=1)
    empty = row <= 0
    flows = np.divide(mass, row[:, None], out=np.zeros_like(mass), where=~empty[:, None])
    return flows, empty


def catchment_population(seat, site_xy):
    """Electoral population of each site's nearest-site catchment (diagnostic)."""
    _, nearest = cKDTree(site_xy).query(seat['xy'])
    return np.bincount(nearest, weights=seat['population'], minlength=len(site_xy))


def polygon_flows(seat, site_xy, polygons, population=None):
    """Point-in-polygon flows: each site wholly in the target seat containing it (snapped to the nearest eligible target).

    `polygons` maps target code to a shapely geometry. Eligible targets are those with positive population from the old seat.
    Returns (F, number of sites outside every eligible polygon).
    """
    pop = seat['population'] if population is None else population
    mass = np.bincount(seat['tindex'], weights=pop, minlength=len(seat['targets']))
    eligible = [k for k, t in enumerate(seat['targets']) if mass[k] > 0]
    flows = np.zeros((len(site_xy), len(seat['targets'])))
    snapped = 0
    for s, (x, y) in enumerate(site_xy):
        point = Point(x, y)
        inside = [k for k in eligible if polygons[seat['targets'][k]].covers(point)]
        if not inside:
            snapped += 1
            inside = [min(eligible, key=lambda k: polygons[seat['targets'][k]].distance(point))]
        flows[s, inside[0]] = 1.0
    return flows, snapped


def allocate(site_votes, nonplace, flows, empty, a, lam):
    """Contribution [T x C] of one old seat. Sites with empty catchments join the non-place pool.

    `b` weights the site flows by each site's valid total (the sum of its vote columns, all valid-vote columns); `lam` mixes
    A (population) and B (vote-weighted place flows).
    """
    votes = site_votes.astype(float)
    pool = nonplace.astype(float) + votes[empty].sum(axis=0)
    keep = ~empty
    placed = flows[keep].T @ votes[keep] if keep.any() else np.zeros((flows.shape[1], votes.shape[1]))
    weights = votes[keep].sum(axis=1)
    if keep.any() and weights.sum() > 0:
        b = (weights[:, None] * flows[keep]).sum(axis=0) / weights.sum()
    else:
        b = a
    mixture = (1 - lam) * a + lam * b
    return placed + np.outer(mixture, pool)
