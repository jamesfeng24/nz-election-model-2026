"""Outcome-free aggregate/within simulation, national scenario shared once."""
import numpy as np
from scripts.uncertainty.streams import normal
from scripts.uncertainty.simulation import candidate_inputs
from scripts.polling.candidate_integration.propagation import local_vectors, candidate_vectors
from .coordinates import inverse, partition
from .estimation import labels


def noise(row, scales, draws):
    key = f"stage45:{row['layer']}:{row['targetYear']}"
    seat = row['targetElectorateId']
    result, total = {}, {}
    for name in ('balance', 'mass'):
        s = scales[name]
        result[name] = s['shared'] * normal(key + ':shared:' + name, draws) + s['seat'] * normal(key + ':seat:' + seat + ':' + name, draws)
        total[name] = float(np.hypot(s['shared'], s['seat']))
    other = partition(row['groups'])[2]
    if other:
        tags = labels(row)
        shared = np.column_stack([normal(key + ':shared:within:' + tags[i], draws) for i in other])
        specific = np.column_stack([normal(key + ':seat:' + seat + ':within:' + row['ids'][i], draws) for i in other])
        eta = scales['within']['shared'] * shared + scales['within']['seat'] * specific
        result['within'] = eta - eta.mean(axis=1, keepdims=True)
    else:
        result['within'] = np.empty((draws, 0))
    return result, total


def component(row, scales, draws):
    eta, total = noise(row, scales, draws)
    q, location = inverse(row['mean'], row['groups'], eta, total)
    return q, {'deterministicMean': row['mean'], 'simulatedMean': q.mean(axis=0).tolist(),
               'meanShiftPP': (100 * (q.mean(axis=0) - row['mean'])).tolist(), 'location': location}


def compose(party, candidate, national, party_scales, candidate_scales):
    deterministic = local_vectors(national, party['affinities'])
    eta, total = noise(party, party_scales, len(national))
    local, location = inverse(deterministic, party['groups'], eta, total)
    destinations, exponent, floor = candidate_inputs(candidate, party)
    conditional = candidate_vectors(local, destinations, exponent, floor)
    eta, total = noise(candidate, candidate_scales, len(national))
    q, candidate_location = inverse(conditional, candidate['groups'], eta, total)
    control = candidate_vectors(deterministic, destinations, exponent, floor)
    return q, {'deterministicNationalOnlyMean': control.mean(axis=0).tolist(),
               'candidateConditionalMeanAfterLocalUncertainty': conditional.mean(axis=0).tolist(),
               'simulatedMean': q.mean(axis=0).tolist(), 'localLocation': location,
               'candidateLocation': candidate_location,
               'meanShiftPP': (100 * (q.mean(axis=0) - control.mean(axis=0))).tolist(),
               'nonlinearShiftPP': (100 * (conditional.mean(axis=0) - control.mean(axis=0))).tolist(),
               'conditionalIntegrationScope': 'balance and major mass; remainder marginal only',
               'nationalRedrawn': False, 'crossLayerIndependenceAssumed': True}
