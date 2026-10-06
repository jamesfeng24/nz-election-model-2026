"""Earlier-trained candidate-balance scale adjustments: exact Gaussian likelihood, ridge, checks."""
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit, roots_hermitenorm
from .common import PREFIX, read, save, verify, arguments, design, STAGE47_CONTRACT
from .data import environments, centers, centered, folds

NODES, WEIGHTS = roots_hermitenorm(81)
WEIGHTS = WEIGHTS / np.sqrt(2 * np.pi)
RIDGE_SD = 0.5
BOUND = float(np.log(4))


def location(p, sd):
    """Gaussian logistic location l with E[expit(l + sd Z)] = p, and dl/dsd (implicit)."""
    p, sd = np.asarray(p, float), np.asarray(sd, float)
    if np.any((p <= 0) | (p >= 1)):
        raise ValueError('Interior ratio mean required')
    loc = logit(p)
    for _ in range(100):
        q = expit(loc[:, None] + sd[:, None] * NODES[None, :])
        gap = q @ WEIGHTS - p
        slope = (q * (1 - q)) @ WEIGHTS
        step = np.clip(gap / slope, -1, 1)
        loc = loc - step
        if np.max(np.abs(step)) < 1e-15:
            break
    q = expit(loc[:, None] + sd[:, None] * NODES[None, :])
    if np.max(np.abs(q @ WEIGHTS - p)) > 1e-13:
        raise ValueError('Location did not converge')
    d = q * (1 - q)
    return loc, -(d * NODES[None, :]) @ WEIGHTS / (d @ WEIGHTS)


def environment_value(theta, p, v, features, seat, shared):
    """Per-seat-normalised negative log likelihood and its gradient for one environment."""
    f = np.column_stack((np.ones(len(p)), features))
    sigma = seat * np.exp(f @ theta)
    total = np.sqrt(shared ** 2 + sigma ** 2)
    loc, dloc = location(p, total)
    r = v - loc
    w = 1 / sigma ** 2
    tau2 = shared ** 2
    denominator = 1 + tau2 * w.sum()
    s = (w * r).sum()
    quad = (w * r * r).sum() - tau2 * s * s / denominator
    logdet = np.log(sigma ** 2).sum() + np.log(denominator)
    g = w * r - tau2 * w * s / denominator
    inverse_diagonal = w - tau2 * w * w / denominator
    dsigma = 2 * sigma * (inverse_diagonal - g * g) - 2 * g * dloc * sigma / total
    gradient = 0.5 / len(p) * ((dsigma * sigma) @ f)
    return 0.5 / len(p) * (logdet + quad), gradient


def objective(theta, training, penalised=True):
    theta = np.asarray(theta, float)
    value, gradient = 0., np.zeros(3)
    for e in training:
        a, b = environment_value(theta, **e)
        value += a; gradient += b
    value /= len(training); gradient /= len(training)
    if penalised:
        value += 0.5 * np.sum((theta / RIDGE_SD) ** 2)
        gradient = gradient + theta / RIDGE_SD ** 2
    return float(value), gradient


def training_set(env, years, center):
    return [{'p': env[y]['p'], 'v': env[y]['v'], 'features': centered(env, y, center),
             'seat': env[y]['seat'], 'shared': env[y]['shared']} for y in years]


def projected(theta, gradient, free):
    g = np.where(free, gradient, 0.)
    g = np.where((theta <= -BOUND + 1e-12) & (g > 0), 0., g)
    return np.where((theta >= BOUND - 1e-12) & (g < 0), 0., g)


def solve(training, free, penalised=True):
    spec = design()
    starts = ([0., 0., 0.], [-0.2, 0., 0.], [0.2, 0., 0.])
    bounds = [(-BOUND, BOUND) if f else (0., 0.) for f in free]
    runs = []
    for start in starts:
        result = minimize(lambda t: objective(t, training, penalised), start, jac=True, method='L-BFGS-B', bounds=bounds,
                          options={'ftol': 1e-12, 'gtol': 1e-8, 'maxiter': 1000})
        runs.append({'start': start, 'theta': result.x.tolist(), 'objective': float(result.fun), 'iterations': int(result.nit),
                     'success': bool(result.success)})
    best = min(range(3), key=lambda i: (round(runs[i]['objective'], 10), i))
    return runs, best


def central_gradient(theta, training, penalised=True, step=1e-5):
    theta = np.asarray(theta, float)
    out = np.zeros(3)
    for i in range(3):
        d = np.zeros(3); d[i] = step
        out[i] = (objective(theta + d, training, penalised)[0] - objective(theta - d, training, penalised)[0]) / (2 * step)
    return out


def hessian(theta, training, penalised=False, step=1e-5):
    theta = np.asarray(theta, float)
    h = np.zeros((3, 3))
    for i in range(3):
        d = np.zeros(3); d[i] = step
        h[i] = (objective(theta + d, training, penalised)[1] - objective(theta - d, training, penalised)[1]) / (2 * step)
    return (h + h.T) / 2


def fit_restriction(training, free):
    runs, best = solve(training, free)
    theta = np.array(runs[best]['theta'])
    value, gradient = objective(theta, training)
    mask = np.array(free)
    powell = minimize(lambda t: objective(np.where(mask, t, 0.), training)[0], np.array(runs[best]['start']), method='Powell',
                      bounds=[(-BOUND, BOUND)] * 3, options={'xtol': 1e-10, 'ftol': 1e-10, 'maxiter': 2000})
    powell_theta = np.where(mask, powell.x, 0.)
    h = hessian(theta, training)[np.ix_(mask, mask)]
    eigen = np.linalg.eigvalsh(h)
    bound_contact = [bool(f and abs(abs(t) - BOUND) < 1e-6) for t, f in zip(theta, mask)]
    return {'theta': theta.tolist(), 'objective': value, 'gradient': gradient.tolist(),
            'projectedGradientMax': float(np.max(np.abs(projected(theta, gradient, mask)))),
            'centralDifferenceGradientMaxDifference': float(np.max(np.abs(central_gradient(theta, training) - gradient))),
            'starts': runs, 'chosenStart': best, 'boundContact': bound_contact,
            'powell': {'theta': powell_theta.tolist(), 'objective': float(powell.fun),
                       'objectiveDifference': abs(float(powell.fun) - value),
                       'maximumParameterDifference': float(np.max(np.abs(powell_theta - theta)))},
            'likelihoodInformation': {'hessianEigenvalues': eigen.tolist(),
                                      'rank': int(np.sum(eigen > 1e-8 * max(np.max(np.abs(eigen)), 1e-300))),
                                      'conditionNumber': float(np.max(eigen) / np.min(eigen)) if np.min(eigen) > 0 else None,
                                      'meaning': 'unpenalised likelihood curvature of the free parameters; penalty reported separately'}}


def unpenalised_constant(training):
    runs, best = solve(training, [True, False, False], penalised=False)
    return {'a': runs[best]['theta'][0], 'objective': runs[best]['objective'],
            'scoredOrAdopted': False, 'status': 'descriptive likelihood-only maximiser of the constant; not a restriction'}


def multipliers(theta, features):
    return np.exp(theta[0] + features @ np.asarray(theta[1:]))


def build():
    env = environments()
    spec = design()
    result = {'stage': 48, 'folds': {}, 'objective': read(STAGE47_CONTRACT)['equations']['objective'],
              'ridgeSD': RIDGE_SD, 'bound': BOUND}
    for year, earlier in folds().items():
        center = centers(env, earlier)
        record = {'targetYear': year, 'trainingYears': earlier, 'centers': center, 'seatIds': env[year]['ids'],
                  'trainingSeats': int(sum(len(env[y]['p']) for y in earlier)),
                  'missingFeatureSeats': {str(y): {k: int(sum(f[k] for f in env[y]['missing'])) for k in ('R', 'T')} for y in [year, *earlier]}}
        features = centered(env, year, center)
        if not earlier:
            zero = {'theta': [0., 0., 0.], 'status': 'no earlier candidate residual: a = b = 0, prior/control'}
            record.update({'control': zero, 'constant': zero, 'conditional': zero})
            record['multipliers'] = {r: [1.] * len(features) for r in spec['restrictions']}
        else:
            training = training_set(env, earlier, center)
            record['constant'] = fit_restriction(training, [True, False, False])
            record['conditional'] = fit_restriction(training, [True, True, True])
            record['control'] = {'theta': [0., 0., 0.], 'status': 'numerically corrected Stage45 control'}
            record['unpenalisedConstant'] = unpenalised_constant(training)
            record['multipliers'] = {r: multipliers(np.array(record[r]['theta']), features).tolist() for r in spec['restrictions']}
        record['multiplierSummary'] = {r: {'min': float(np.min(m)), 'median': float(np.median(m)), 'max': float(np.max(m))}
                                       for r, m in record['multipliers'].items()}
        result['folds'][str(year)] = record
    return result


def main():
    args = arguments()
    verify()
    save('fit.json', build(), args.check, tolerance=read(PREFIX + '/design-contract.json')['fitCheckParameterTolerance'])
    print('Stage48 earlier-trained scale adjustments fitted' if not args.check else 'Stage48 fits reproduced')


if __name__ == '__main__':
    main()
