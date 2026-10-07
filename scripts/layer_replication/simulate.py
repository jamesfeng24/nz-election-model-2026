"""One layer replicate of a composed control bank on the whole national pool, with exact reuse of the local-layer solves."""
import contextlib
import hashlib
import numpy as np
from scripts.composed_precision.simulate import composed_bank, winner_probabilities
from scripts.uncertainty_expectation import simulation as expectation
from scripts.uncertainty_tails.metrics import record


@contextlib.contextmanager
def reused_solves():
    """Share conditional-location solves between calls with identical inputs (same bytes, tags and scales).

    ``invert`` computes the offsets of the local-party layer from the national draw alone, so the same inputs recur
    in every layer replicate; the candidate layer's inputs depend on the replicate's local draws and never recur. A hit
    returns the very object the first call computed, so the result equals the uncached path exactly."""
    original = expectation.solve_locations
    cache, counts = {}, {'hits': 0, 'misses': 0}

    def cached(unique, tags, shared, seat):
        key = (hashlib.sha256(np.ascontiguousarray(unique).tobytes()).digest(), unique.shape, tuple(tags), shared, seat)
        if key in cache:
            counts['hits'] += 1
        else:
            counts['misses'] += 1
            cache[key] = original(unique, tags, shared, seat)
        return cache[key]

    expectation.solve_locations = cached
    try:
        yield counts
    finally:
        expectation.solve_locations = original


def replicate_bank(row, party, national, party_scales, fit, scramble):
    """The control bank of one replicate and the national-only control input (identical for every replicate)."""
    banks, control_input, _, _ = composed_bank(row, party, national, party_scales, fit, {}, scramble, ('control',))
    return banks['control'], np.asarray(control_input)


def bank_metrics(row, q, point):
    """Per-candidate gate quantities and win probabilities of one bank."""
    rec = record(row, q, point)
    return {'meansPP': [float(100 * v) for v in rec['simulatedMean']], 'crps': [float(v) for v in rec['crpsPP']],
            'energy': float(rec['energyPP']), **{f'width{v}': [float(x) for x in rec[f'interval{v}']['widths']] for v in (50, 80, 90)},
            'win': [float(v) for v in winner_probabilities(q)]}
