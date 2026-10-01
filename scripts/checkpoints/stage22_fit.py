"""Frozen, deterministic Stage22 conditional complete-share fits."""

from fractions import Fraction
from math import isfinite

import numpy as np
from scipy.optimize import minimize, minimize_scalar, shgo


LOW, HIGH = 0.0001, 0.1
THETA_BOUNDS = (-4.0, 4.0)
METHODS = ('baseline', 'baseline_plus_S', 'baseline_plus_V',
           'baseline_plus_S_plus_V')
SCENARIOS = ('printed', 'selected_lower', 'selected_upper')


def choose_tied(options, parameter):
    minimum = min(item[0] for item in options)
    tied = [item for item in options if item[0] <= minimum + 1e-12]
    return min(tied, key=lambda item: parameter(item[1]))


def source_s(candidate, scenario):
    if candidate['s0Reported'] is None:
        return None
    if scenario == 'printed':
        return candidate['s0Reported']
    endpoint = 0 if scenario == 'selected_lower' else 1
    return float(Fraction(candidate['coupledSamePartyPercent'][endpoint]) / 100)


def means_for_training(rows, scenario):
    values = {'S': [0.0, 0.0], 'V': [0.0, 0.0]}
    for seat in rows:
        weight = 1 / len(seat['candidates'])
        for candidate in seat['candidates']:
            for name, value in (('S', source_s(candidate, scenario)),
                                ('V', candidate['v0'])):
                if value is not None:
                    values[name][0] += weight * value
                    values[name][1] += weight
    if any(values[key][1] <= 0 for key in values):
        raise ValueError('No supported training feature')
    return {key: pair[0] / pair[1] for key, pair in values.items()}


def candidate_arrays(rows, means, scenario):
    bases, sx, vx, starts = [], [], [], []
    for seat in rows:
        starts.append(len(bases))
        for candidate in seat['candidates']:
            support = candidate['targetPartySupport']
            if support is None or not isfinite(support) or support < 0:
                raise ValueError('Invalid complete candidate baseline')
            bases.append(support)
            s = source_s(candidate, scenario)
            v = candidate['v0']
            sx.append(s - means['S'] if s is not None else 0.0)
            vx.append(v - means['V'] if v is not None else 0.0)
    return np.array(bases), np.array([sx, vx]).T, np.array(starts)


def earlier_actuals(rows, elections):
    """Read only completed prior elections for the holdout's training IDs."""
    shares = []
    seats = {seat['id']: seat for doc in elections.values()
             for seat in doc['electorates']}
    for row in rows:
        seat = seats[row['targetElectorateId']]
        ballot = seat['candidateBallot']
        valid = ballot['validVotes']
        totals = {candidate['id']: candidate['votes'] for candidate in seat['candidates']}
        ids = [candidate['targetOccurrenceId'] for candidate in row['candidates']]
        if (valid <= 0 or valid != seat['validCandidateVotes'] or
                sum(totals.values()) != valid or set(totals) != set(ids) or
                len(ids) != len(set(ids))):
            raise ValueError('Earlier candidate outcomes do not reconcile')
        shares.extend(totals[cid] / valid for cid in ids)
    return np.array(shares)


def selected_columns(method):
    return {'baseline': (), 'baseline_plus_S': (0,),
            'baseline_plus_V': (1,), 'baseline_plus_S_plus_V': (0, 1)}[method]


class Profile:
    def __init__(self, base, features, starts, actual, method):
        self.base = base
        self.features = features[:, selected_columns(method)]
        self.starts = starts
        self.actual = actual
        self.contests = len(starts)
        if not self.contests or len(base) != len(actual) or abs(
                sum(actual) - self.contests) > 1e-8:
            raise ValueError('Invalid complete training slates')
        self.cache = {}

    def value_gradient(self, kappa, theta):
        if not LOW <= kappa <= HIGH:
            raise ValueError('Floor outside frozen bounds')
        z = np.log(self.base + kappa) + self.features @ theta
        max_each = np.maximum.reduceat(z, self.starts)
        shifted = np.exp(z - np.repeat(max_each, np.diff(
            np.r_[self.starts, len(z)])))
        totals = np.add.reduceat(shifted, self.starts)
        probs = shifted / np.repeat(totals, np.diff(np.r_[self.starts, len(z)]))
        losses = max_each + np.log(totals) - np.add.reduceat(self.actual * z,
                                                              self.starts)
        loss = float(np.mean(losses))
        gradient = self.features.T @ (probs - self.actual) / self.contests
        if not np.isfinite(loss) or not np.all(np.isfinite(gradient)):
            raise ValueError('Nonfinite profile objective')
        return float(loss), gradient

    def theta_optimum(self, kappa):
        key = float(kappa)
        if key in self.cache:
            return self.cache[key]
        if not self.features.shape[1]:
            loss = self.value_gradient(key, np.empty(0))[0]
            result = (loss, np.empty(0), 0.0)
        else:
            results = []
            starts = [np.array(x, dtype=float) for x in
                      np.array(np.meshgrid(*[[-2.0, 0.0, 2.0]] *
                                           self.features.shape[1])).T.reshape(
                                               -1, self.features.shape[1])]
            for initial in starts:
                solution = minimize(lambda theta: self.value_gradient(key, theta),
                                    initial, method='L-BFGS-B', jac=True,
                                    bounds=[THETA_BOUNDS] * len(initial),
                                    options={'ftol': 1e-15, 'gtol': 1e-11,
                                             'maxiter': 2000, 'maxls': 50})
                if not isfinite(solution.fun):
                    raise ValueError('Theta optimizer nonfinite')
                loss, gradient = self.value_gradient(key, solution.x)
                projected = gradient.copy()
                for i, value in enumerate(solution.x):
                    if value <= THETA_BOUNDS[0] + 1e-8 and projected[i] > 0:
                        projected[i] = 0
                    if value >= THETA_BOUNDS[1] - 1e-8 and projected[i] < 0:
                        projected[i] = 0
                norm = float(np.max(np.abs(projected)))
                if norm > 1e-7:
                    raise ValueError('Theta projected gradient failed')
                results.append((loss, solution.x, norm))
            if max(item[0] for item in results) - min(item[0] for item in results) > 1e-8:
                raise ValueError('Theta fixed-start objectives disagree')
            result = choose_tied(results, lambda theta: tuple(theta))
        self.cache[key] = result
        return result


def independent_profile(profile):
    grid = np.linspace(LOW, HIGH, 4097)
    values = np.array([profile.theta_optimum(float(x))[0] for x in grid])
    minima = [i for i in range(1, len(grid) - 1)
              if values[i] <= values[i - 1] and values[i] <= values[i + 1]]
    options = [(float(values[0]), LOW), (float(values[-1]), HIGH)]
    for i in minima:
        result = minimize_scalar(lambda k: profile.theta_optimum(k)[0],
                                 method='bounded', bounds=(grid[i - 1], grid[i + 1]),
                                 options={'xatol': 1e-14})
        if not result.success:
            raise ValueError('Independent profile refinement failed')
        options.append((float(result.fun), float(result.x)))
    return choose_tied(options, float)


def fit(profile):
    objective = lambda x: profile.theta_optimum(float(x[0]))[0]
    solution = shgo(objective, [(LOW, HIGH)], n=256, iters=2,
                    sampling_method='sobol', options={'f_tol': 1e-12})
    if not solution.success or not isfinite(solution.fun):
        raise ValueError('Kappa SHGO failed')
    options = [(profile.theta_optimum(k)[0], k)
               for k in (LOW, HIGH, float(solution.x[0]))]
    options += [(profile.theta_optimum(float(row[0]))[0], float(row[0]))
                for row in solution.xl]
    primary = choose_tied(options, float)
    independent = independent_profile(profile)
    if (abs(primary[0] - independent[0]) > 1e-8 or
            (abs(primary[1] - independent[1]) > 1e-4 and
             abs(primary[0] - independent[0]) > 1e-12)):
        raise ValueError('Independent kappa profile disagrees')
    theta = profile.theta_optimum(primary[1])[1]
    return {'status': 'fitted', 'kappa': primary[1],
            'theta': [float(x) for x in theta], 'objective': primary[0],
            'independentKappa': independent[1], 'independentObjective': independent[0],
            'boundary': ('lower' if primary[1] <= LOW + 1e-7 else
                         'upper' if primary[1] >= HIGH - 1e-7 else 'interior'),
            'thetaAtBoundary': [bool(abs(x - THETA_BOUNDS[0]) < 1e-7 or
                                     abs(x - THETA_BOUNDS[1]) < 1e-7) for x in theta],
            'projectedGradientInfinity': profile.theta_optimum(primary[1])[2]}


def predict(rows, means, scenario, method, parameters):
    base, all_features, starts = candidate_arrays(rows, means, scenario)
    features = all_features[:, selected_columns(method)]
    theta = np.array(parameters['theta'])
    z = np.log(base + parameters['kappa']) + features @ theta
    result = []
    for i, row in enumerate(rows):
        stop = starts[i + 1] if i + 1 < len(starts) else len(z)
        block = z[starts[i]:stop]
        shifted = np.exp(block - max(block))
        shares = shifted / sum(shifted)
        if not np.all(np.isfinite(shares)) or abs(sum(shares) - 1) > 1e-12:
            raise ValueError('Predicted candidate shares do not conserve')
        result.append({'targetElectorateId': row['targetElectorateId'],
                       'candidateShares': {c['targetOccurrenceId']: float(s)
                                           for c, s in zip(row['candidates'], shares)}})
    return result
