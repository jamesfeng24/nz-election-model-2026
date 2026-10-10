"""General seats: local party layer, then candidate layer with the D107 seat multiplier, then winners.

Rows follow the Stage44 inventory shapes so the frozen Stage47 inversion (`invert`) and the Stage42/43 candidate
transform (`candidate_vectors`) run unchanged. Means come from the configured baseline and the latest saved S+R fit;
scales from the Stage72 2026 file; the only per-seat choice is the classification multiplier.
"""
from copy import deepcopy
import numpy as np
from scripts.polling.candidate_integration.propagation import local_vectors, candidate_vectors
from scripts.party_vote_elasticity.transforms import ARMS, swing, swing_mixture
from scripts.uncertainty.simulation import candidate_inputs
from scripts.uncertainty_expectation.simulation import invert
from scripts.uncertainty_revision.coordinates import partition
from scripts.seat_polls.apply import apply as apply_poll
from .common import YEAR, OTHER, read, require, exact, namespace_seed


def role(key):
    return {'nationalparty': 'national', 'labourparty': 'labour'}.get(key, 'other')


def seat_id(code):
    return f'nz-general-{YEAR}-boundary-{code}'


def relationships(config):
    """2023 ballot-group key -> 2026 key, for documented continuing parties only."""
    records = read(config['partyRelationships'])['records']
    return {r['sourceBallotGroupKey']: r['targetGroupKey'] for r in records
            if r['sourceBallotGroupKey'] and r['continuity'].startswith('documented_')}


def baseline(config):
    scope = read(config['baseline']['source'])['transitions']['2023-2026']['scopes']['general']
    keys = scope['partyCategories']
    national = np.array([exact(scope['nationalSourceSharesExact'][k]) for k in keys])
    seats = {}
    for target in scope['targetPartyVectors']:
        shares = {p['partyKey']: exact(p['shareExact']) for p in target['parties']}
        require(set(shares) == set(keys), f"baseline seat {target['targetCode']} has a different party roster")
        seats[seat_id(target['targetCode'])] = np.array([shares[k] for k in keys])
    return keys, national, seats


def fine_national(draws, groups, keys, national2023, continuing):
    """Per-draw national vector over the baseline keys. Core parties take their own category; Other is split in
    proportion to the 2023 national shares, so that inside a seat (after the affinities) Other follows that seat's own
    2023 mix. The national MMP party vote keeps Other as one bucket."""
    other = groups.index(OTHER)
    column = {g: i for i, g in enumerate(groups) if g != OTHER}
    core = [continuing.get(k) in column for k in keys]
    for g in column:
        require(any(continuing.get(k) == g for k in keys), f'national group {g} has no baseline party')
    rest = national2023 * ~np.array(core)
    require(rest.sum() > 0, 'no 2023 national mass outside the core parties')
    weights = rest / rest.sum()
    x = np.empty((len(draws), len(keys)))
    for j, k in enumerate(keys):
        x[:, j] = draws[:, column[continuing[k]]] if core[j] else draws[:, other] * weights[j]
    return x


def party_row(electorate, keys, local, national2023, continuing):
    require(np.isfinite(local).all() and abs(local.sum() - 1) < 1e-9, f'{electorate}: baseline is not a simplex')
    require(not ((national2023 == 0) & (local > 0)).any(), f'{electorate}: local share without national share')
    affinities = np.divide(local, national2023, out=np.zeros_like(local), where=national2023 > 0)
    groups = [continuing.get(k, f'source2023:{k}') for k in keys]
    return {'layer': 'local_party', 'targetYear': YEAR, 'targetElectorateId': electorate, 'ids': list(keys),
            'ballotGroupKeys': groups, 'groups': [role(g) for g in groups], 'affinities': affinities.tolist(),
            'mean': local.tolist()}


def fold_parameters(config):
    spec = config['candidate']['fold']
    folds = read(config['candidate']['parameters'])['folds']
    matches = [f for f in folds if f['branch'] == spec['branch'] and f['targetYear'] == spec['targetYear']]
    require(len(matches) == 1, 'candidate parameter fold not found exactly once')
    fit = matches[0]['fits'][spec['method']]
    require(fit['parameters']['status'] == 'fitted', 'candidate parameter fold is not fitted')
    centred = read(config['candidate']['centredFeatures'])
    require(centred['fitId'] == fit['fitId'] and centred['trainingOnlyMeans'] == matches[0]['trainingOnlyMeans'],
            'the 2026 candidate features are not centred on the configured fit')
    return fit['parameters'], fit['fitId']


def candidate_row(electorate, slate, party, parameters):
    """slate: [{id, group (2026 key or None), S, R}]; centred continuous S/R contributions as Stage43 rows."""
    require(len(slate) >= 2 and len({c['id'] for c in slate}) == len(slate), f'{electorate}: incomplete or duplicate slate')
    lookup = set(party['ballotGroupKeys'])
    features = [{'id': c['id'], 'group': c['group'] if c['group'] in lookup else None, 'centered': [float(c['S']), float(c['R'])]}
                for c in slate]
    groups = ['no_group' if f['group'] is None else role(f['group']) for f in features]
    require(groups.count('national') <= 1 and groups.count('labour') <= 1, f'{electorate}: duplicate major candidate')
    return {'layer': 'candidate', 'targetYear': YEAR, 'targetElectorateId': electorate, 'ids': [c['id'] for c in slate],
            'groups': groups, 'features': features, 'parameters': parameters,
            'partyOf': [c['group'] for c in slate]}


def scaled(scales, multiplier):
    result = deepcopy(scales)
    result['balance']['seat'] = scales['balance']['seat'] * float(multiplier)
    return result


def local_transform(config):
    """Stage81 (D119): None keeps the frozen proportional layer exactly; otherwise a function (party row, fine draws, national
    2023, rows per national draw) -> deterministic local vectors for 'P', 'A', 'L', 'H' or an equal-weight per-national-draw
    mixture ('mixture' with `arms`). The default configuration carries no `localParty` key."""
    setting = config.get('localParty')
    if not setting:
        return None
    name = setting['transform']
    arms = setting.get('arms')
    require(name in ARMS or (name == 'mixture' and arms and set(arms) <= set(ARMS)), f'unknown localParty.transform {name!r}')
    if name in ARMS:
        return lambda party, fine, national2023, replicates: swing(name, np.array(party['mean']), national2023, fine)
    seed = namespace_seed(config['simulation']['seedNamespace'], 'localParty-transform')

    def mixture(party, fine, national2023, replicates):
        draws = len(fine) // replicates
        assignment = np.repeat(np.array(arms)[np.random.default_rng(seed).integers(0, len(arms), size=draws)], replicates)
        return swing_mixture(arms, assignment, np.array(party['mean']), national2023, fine)
    return mixture


def simulate(party, candidate, fine, party_scales, candidate_scales, multiplier, deterministic=None):
    """Candidate shares [count, C] for one seat; the multiplier touches only the candidate balance seat scale."""
    local, q, _ = simulate_with_poll(party, candidate, fine, party_scales, candidate_scales, multiplier, None, deterministic)
    return local, q


def simulate_with_poll(party, candidate, fine, party_scales, candidate_scales, multiplier, poll, deterministic=None):
    """As `simulate`, plus the Stage79 seat-poll update of the balance when `poll` is given (record returned third)."""
    count = len(fine)
    if deterministic is None:
        deterministic = local_vectors(fine, party['affinities'])
    local, _ = invert(deterministic, party, party_scales, count)
    if candidate is None:
        return local, None, None
    destinations, exponents, kappa = candidate_inputs(candidate, party)
    conditional = candidate_vectors(local, destinations, exponents, kappa)
    record = None
    if poll is not None and all(partition(candidate['groups'])[:2]):  # no National or no Labour candidate: no balance to update
        conditional, candidate_scales, record = apply_poll(conditional, candidate, candidate_scales, multiplier, poll)
    q, _ = invert(conditional, candidate, scaled(candidate_scales, multiplier), count)
    return local, q, record
