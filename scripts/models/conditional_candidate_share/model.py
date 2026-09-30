"""Frozen one-parameter conditional candidate-share construction."""

from collections import Counter, defaultdict
from math import isfinite, log

import numpy as np
from scipy.optimize import minimize_scalar, shgo

from scripts.checkpoints.candidate_share_design import candidate_shares


LOW, HIGH = 0.0001, 0.1
TRAINING = {2011: (2008,), 2017: (2008, 2011, 2014),
            2023: (2008, 2011, 2014, 2017, 2020)}
METHODS = ('fitted_floor', 'uniform', 'restricted_zero_floor')


def observed_party_vector(seat):
    """Build a complete party-valid vector without candidate outcome fields."""
    groups = seat['parties']
    valid = seat['partyBallot']['validVotes']
    if (valid <= 0 or valid != seat['validPartyVotes'] or
            sum(row['votes'] for row in groups) != valid or
            len({row['partyKey'] for row in groups}) != len(groups)):
        raise ValueError('Incompatible observed party-valid ballot population')
    return {row['partyKey']: row['votes'] / valid for row in groups}


def slate_for_kernel(candidates):
    return [{'candidateId': row['candidateOccurrenceId'],
             'partyKey': row['partyKey'],
             'noRegisteredPartyGroup': row['noRegisteredPartyGroup']}
            for row in candidates]


def training_cases(target_year, inventory, elections):
    """Read only completed earlier candidate outcomes for this target year."""
    cases = []
    by_seat = {(year, seat['id']): seat for year, doc in elections.items()
               for seat in doc['electorates'] if seat['kind'] == 'general'}
    for row in inventory['trainingGeneralContests']:
        if row['year'] not in TRAINING[target_year] or row['status'] != 'complete':
            continue
        seat = by_seat[(row['year'], row['electorateId'])]
        party = observed_party_vector(seat)
        valid = seat['candidateBallot']['validVotes']
        results = {candidate['id']: candidate['votes'] for candidate in seat['candidates']}
        if (valid <= 0 or valid != seat['validCandidateVotes'] or
                sum(results.values()) != valid or
                set(results) != {candidate['candidateOccurrenceId'] for candidate in row['candidates']}):
            raise ValueError('Incompatible earlier candidate-valid ballot population')
        bases = np.array([party[candidate['partyKey']] if candidate['partyKey'] is not None
                          else 0.0 for candidate in row['candidates']], dtype=float)
        shares = np.array([results[candidate['candidateOccurrenceId']] / valid
                           for candidate in row['candidates']], dtype=float)
        cases.append({'id': seat['id'], 'year': row['year'], 'base': bases,
                      'actual': shares,
                      'hasNoGroupOrZeroSupport': any(value == 0 for value in bases)})
    return cases


def cross_entropy(kappa, cases):
    if not isfinite(kappa) or kappa < LOW or kappa > HIGH:
        raise ValueError('Floor outside frozen interval')
    loss = 0.0
    for case in cases:
        weights = case['base'] + kappa
        total = float(np.sum(weights))
        loss += log(total) - float(np.dot(case['actual'], np.log(weights)))
    return loss / len(cases)


def independent_minimum(cases):
    grid = np.linspace(LOW, HIGH, 4097)
    values = np.zeros(len(grid))
    for case in cases:
        weights = case['base'][:, None] + grid[None, :]
        values += (np.log(np.sum(weights, axis=0)) -
                   np.sum(case['actual'][:, None] * np.log(weights), axis=0))
    values /= len(cases)
    candidate_indices = [i for i in range(1, len(grid) - 1)
                         if values[i] <= values[i - 1] and values[i] <= values[i + 1]]
    options = [(float(values[0]), LOW), (float(values[-1]), HIGH)]
    for index in candidate_indices:
        local = minimize_scalar(lambda x: cross_entropy(x, cases),
                                bounds=(grid[index - 1], grid[index + 1]),
                                method='bounded', options={'xatol': 1e-14})
        if not local.success:
            raise ValueError('Independent local optimization failed')
        options.append((float(local.fun), float(local.x)))
    return min(options, key=lambda item: (item[0], item[1]))


def fit_floor(cases):
    if len(cases) < 20 or sum(case['hasNoGroupOrZeroSupport'] for case in cases) < 5:
        return {'status': 'insufficient_training', 'kappa': None,
                'completeTrainingContests': len(cases),
                'noGroupOrZeroSupportTrainingContests': sum(
                    case['hasNoGroupOrZeroSupport'] for case in cases)}
    objective = lambda x: cross_entropy(float(x[0]), cases)
    solution = shgo(objective, [(LOW, HIGH)], n=256, iters=2,
                    sampling_method='sobol', options={'f_tol': 1e-12})
    if not solution.success or not isfinite(solution.fun):
        raise ValueError('SHGO did not converge')
    options = [(cross_entropy(x, cases), x) for x in (LOW, HIGH, float(solution.x[0]))]
    options += [(cross_entropy(float(x[0]), cases), float(x[0]))
                for x in solution.xl]
    primary = min(options, key=lambda item: (item[0], item[1]))
    independent = independent_minimum(cases)
    if (abs(primary[0] - independent[0]) > 1e-8 or
            (abs(primary[1] - independent[1]) > 1e-4 and
             abs(primary[0] - independent[0]) > 1e-12)):
        raise ValueError('Independent optimizer disagrees')
    kappa = round(primary[1], 12)
    return {'status': 'fitted', 'kappa': kappa,
            'objective': round(cross_entropy(kappa, cases), 12),
            'boundary': ('lower' if kappa <= LOW + 1e-7 else
                         'upper' if kappa >= HIGH - 1e-7 else 'interior'),
            'shgoSuccess': True, 'independentObjective': round(independent[0], 12),
            'independentKappa': round(independent[1], 12),
            'completeTrainingContests': len(cases),
            'noGroupOrZeroSupportTrainingContests': sum(
                case['hasNoGroupOrZeroSupport'] for case in cases),
            'trainingByElection': dict(sorted(Counter(case['year'] for case in cases).items()))}


def winner_set(shares):
    maximum = max(shares.values())
    return sorted(key for key, value in shares.items() if maximum - value <= 1e-12)


def predict(candidates, party, kappa):
    slate = slate_for_kernel(candidates)
    fitted = candidate_shares(slate, party, kappa)['candidateShares']
    uniform = {row['candidateOccurrenceId']: 1 / len(candidates) for row in candidates}
    restricted = None
    if all(row['partyKey'] is not None and party[row['partyKey']] > 0 for row in candidates):
        total = sum(party[row['partyKey']] for row in candidates)
        restricted = {row['candidateOccurrenceId']: party[row['partyKey']] / total
                      for row in candidates}
    return {'fitted_floor': fitted, 'uniform': uniform,
            'restricted_zero_floor': restricted}


def transformed_party_vector(seat, rows, method):
    """Accept only a complete coherent Stage 5 joint point, never fill/normalize."""
    keys = {row['partyKey'] for row in seat['parties']}
    if len(rows) != len(keys) or {row['canonicalPartyId'] for row in rows} != keys:
        return None, 'incomplete_party_category_coverage'
    vector = {}
    for row in rows:
        prediction = row['predictions'][method]
        point = prediction['point']
        if (point is None or not isfinite(point) or point < 0 or
                prediction['clippingPossible'] or
                abs(prediction['upper'] - prediction['lower']) > 1e-12):
            return None, 'nondegenerate_or_invalid_party_input'
        vector[row['canonicalPartyId']] = point
    if abs(sum(vector.values()) - 1) > 1e-9:
        return None, 'party_vector_not_jointly_normalized'
    return vector, None


def construct_holdout(year, inventory, elections, stage5_rows):
    cases = training_cases(year, inventory, elections)
    fit = fit_floor(cases)
    seats = {seat['id']: seat for seat in elections[year]['electorates']
             if seat['kind'] == 'general'}
    by_stage5 = defaultdict(list)
    for row in stage5_rows:
        if row['targetYear'] == year:
            by_stage5[row['electorateId']].append(row)
    records = []
    for frame in inventory['frame']:
        if frame['targetYear'] != year:
            continue
        basic = {key: frame[key] for key in ('sourceYear', 'targetYear',
                                            'targetElectorateId', 'scope', 'candidateCount')}
        if frame['status'] != 'complete':
            records.append(basic | {'status': 'abstain', 'reason': frame['status']})
            continue
        if fit['status'] != 'fitted':
            records.append(basic | {'status': 'abstain', 'reason': fit['status']})
            continue
        seat = seats[frame['targetElectorateId']]
        party = observed_party_vector(seat)
        candidates = frame['candidates']
        methods = predict(candidates, party, fit['kappa'])
        sensitivity = {}
        for method in ('additive', 'proportional', 'log_odds'):
            vector, reason = transformed_party_vector(
                seat, by_stage5[seat['id']], method)
            sensitivity[method] = ({'status': 'unsupported', 'reason': reason} if reason else
                                   {'status': 'constructed', 'shares': candidate_shares(
                                       slate_for_kernel(candidates), vector,
                                       fit['kappa'])['candidateShares']})
        records.append(basic | {'status': 'constructed',
                                'partyInput': 'observed_target_local_valid_party_share',
                                'candidates': candidates,
                                'methods': {key: ({'shares': value,
                                                  'predictedWinnerSet': winner_set(value)}
                                                 if value is not None else None)
                                            for key, value in methods.items()},
                                'stage5ConditionalObservedNationalSensitivity': sensitivity})
    return {'targetYear': year, 'trainingYears': list(TRAINING[year]),
            'fit': fit, 'records': records}


def construct(inventory, elections, stage5_rows):
    holdouts = [construct_holdout(year, inventory, elections, stage5_rows)
                for year in (2011, 2017, 2023)]
    records = [row for holdout in holdouts for row in holdout['records']]
    if len(records) != 213:
        raise ValueError('Changed fixed frame')
    return {'schemaVersion': 1, 'stage': 18,
            'mode': 'conditional_observed_local_party_not_pre_election_forecast',
            'outcomeFieldsUsedForTargetConstruction': [], 'holdouts': holdouts,
            'summary': {'frameContests': len(records),
                        'statusByYear': {f'{y}:{status}': n for (y, status), n in sorted(
                            Counter((r['targetYear'], r['status'] if r['status'] == 'constructed'
                                     else r['reason']) for r in records).items())}},
            'selectedOperationalCandidateBaseline': None}
