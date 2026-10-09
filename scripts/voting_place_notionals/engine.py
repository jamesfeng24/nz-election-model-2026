"""Run the allocation arms and the uncertainty draws for one vote kind (candidate-by-label or party columns)."""
import numpy as np

from . import allocate as al
from .sites import split_table

ARMS = ('V', 'P', 'S', 'O', 'A')


def prepare(kind_tables, projections, located, source_of):
    """Per old seat: site venues (canonical order), site vote matrix [S x L], non-place and unlocated vectors [L]."""
    prepared = {}
    for number, table in kind_tables.items():
        sites, matrix, other, unlocated = split_table(table, located)
        projection = projections[number]
        prepared[number] = {'sites': sites, 'matrix': matrix @ projection, 'other': other @ projection,
                            'unlocated': unlocated @ projection, 'source': source_of[number]}
    return prepared


def site_xy(item, located):
    return np.array([[located[v]['x'], located[v]['y']] for v in item['sites']]).reshape(len(item['sites']), 2)


def arms(prepared, seats, located, polygons2025):
    """Arm results {arm: {file number: [T x L]}} and per-seat diagnostics (unperturbed, deterministic)."""
    out = {arm: {} for arm in ARMS}
    diagnostics = {}
    for number, item in prepared.items():
        seat = seats[item['source']]
        xy = site_xy(item, located)
        a = al.population_flow(seat)
        flows, empty = al.nearest_flows(seat, xy)
        votes, other = item['matrix'], item['other']
        out['V'][number] = al.allocate(votes, other, flows, empty, a, 0.0)
        out['S'][number] = al.allocate(votes, other, flows, empty, a, 1.0)
        out['A'][number] = np.outer(a, votes.sum(axis=0) + other)
        keep = ~empty
        out['O'][number] = flows[keep].T @ votes[keep].astype(float)
        pf, snapped = al.polygon_flows(seat, xy, polygons2025)
        out['P'][number] = al.allocate(votes, other, pf, np.zeros(len(xy), dtype=bool), a, 0.0)
        diagnostics[number] = {'sites': len(item['sites']), 'emptyCatchmentSites': int(empty.sum()), 'snappedSites': int(snapped)}
    return out, diagnostics


def draw(prepared_kinds, seats, located, jitter, population, lam):
    """One uncertainty draw: {kind: {file number: [T x L]}}; `jitter` maps venue -> (dx, dy) so a venue moves identically in every file."""
    result = {kind: {} for kind in prepared_kinds}
    for kind, prepared in prepared_kinds.items():
        for number, item in prepared.items():
            seat = seats[item['source']]
            pop = population[item['source']]
            xy = site_xy(item, located) + np.array([jitter[v] for v in item['sites']]).reshape(len(item['sites']), 2)
            a = al.population_flow(seat, pop)
            flows, empty = al.nearest_flows(seat, xy, pop)
            result[kind][number] = al.allocate(item['matrix'], item['other'], flows, empty, a, lam)
    return result


def to_targets(per_seat, seats, source_of):
    """Sum per-old-seat [T_i x L] contributions into {target code: vector [L]}."""
    totals = {}
    for number, matrix in per_seat.items():
        targets = seats[source_of[number]]['targets']
        for k, target in enumerate(targets):
            totals[target] = totals.get(target, 0.0) + matrix[k]
    return totals
