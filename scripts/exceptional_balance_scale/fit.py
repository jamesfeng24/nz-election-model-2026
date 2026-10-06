"""Stage67 two-group arms: earlier-trained, penalty-free ordinary/exceptional seat-balance multipliers."""
import numpy as np
from scipy.optimize import minimize
from scripts.balance_scale.data import environments
from scripts.balance_scale.fit import BOUND, central_gradient, objective, projected, solve
from .common import PREFIX, STAGE60_FIT, YEARS, FLAG_SETS, read, save, verify, arguments, design, indicator, names

FREE = [True, True, False]


def training(env, years, kind, lookup):
    """Stage48 environments with features (flag, 0): seat sd = frozen seat * exp(a + b * flag)."""
    out = []
    for y in years:
        flag = indicator(env[y]['ids'], y, kind, lookup)
        out.append({'p': env[y]['p'], 'v': env[y]['v'], 'features': np.column_stack((flag, np.zeros(len(flag)))),
                    'seat': env[y]['seat'], 'shared': env[y]['shared']})
    return out


def fit_two_group(train):
    runs, best = solve(train, FREE, penalised=False)
    theta = np.array(runs[best]['theta'])
    value, gradient = objective(theta, train, penalised=False)
    mask = np.array(FREE)
    # Independent check over the two free parameters only (an inert third coordinate stalls Powell's line searches).
    powell = minimize(lambda t: objective(np.array([t[0], t[1], 0.]), train, penalised=False)[0], np.array(runs[best]['start'][:2]),
                      method='Powell', bounds=[(-BOUND, BOUND)] * 2,
                      options={'xtol': 1e-10, 'ftol': 1e-12, 'maxiter': 20000, 'maxfev': 200000})
    a, b = float(theta[0]), float(theta[1])
    return {'a': a, 'b': b, 'ordinaryMultiplier': float(np.exp(a)), 'exceptionalMultiplier': float(np.exp(a + b)), 'ratio': float(np.exp(b)),
            'objective': value, 'gradient': gradient.tolist(),
            'projectedGradientMax': float(np.max(np.abs(projected(theta, gradient, mask)))),
            'centralDifferenceGradientMaxDifference': float(np.max(np.abs(central_gradient(theta, train, penalised=False) - gradient))),
            'starts': runs, 'chosenStart': best, 'boundContact': [bool(abs(abs(t) - BOUND) < 1e-6) for t in (a, b)],
            'powell': {'objective': float(powell.fun), 'objectiveDifference': abs(float(powell.fun) - value),
                       'maximumParameterDifference': float(np.max(np.abs(powell.x - theta[:2])))}}


def fit_exc1(train):
    """Amendment 1: flagged seats held at the frozen scale; seat sd = frozen seat * exp(c * (1 - flag)), c fitted."""
    flipped = [{**e, 'features': np.column_stack((1. - e['features'][:, 0], np.zeros(len(e['p']))))} for e in train]
    mask = [False, True, False]
    runs, best = solve(flipped, mask, penalised=False)
    theta = np.array(runs[best]['theta'])
    value, gradient = objective(theta, flipped, penalised=False)
    powell = minimize(lambda t: objective(np.array([0., t[0], 0.]), flipped, penalised=False)[0], np.array([0.]),
                      method='Powell', bounds=[(-BOUND, BOUND)], options={'xtol': 1e-10, 'ftol': 1e-12, 'maxiter': 20000})
    c = float(theta[1])
    return {'c': c, 'ordinaryMultiplier': float(np.exp(c)), 'exceptionalMultiplier': 1.0, 'objective': value, 'gradient': gradient.tolist(),
            'projectedGradientMax': float(np.max(np.abs(projected(theta, gradient, np.array(mask))))),
            'centralDifferenceGradientMaxDifference': float(abs(central_gradient(theta, flipped, penalised=False)[1] - gradient[1])),
            'starts': runs, 'chosenStart': best, 'boundContact': [bool(abs(abs(c) - BOUND) < 1e-6)],
            'powell': {'objective': float(powell.fun), 'objectiveDifference': abs(float(powell.fun) - value),
                       'maximumParameterDifference': float(abs(powell.x[0] - c))}}


def control_fit():
    return {'a': 0.0, 'b': 0.0, 'ordinaryMultiplier': 1.0, 'exceptionalMultiplier': 1.0, 'ratio': 1.0,
            'status': 'no earlier candidate residual: control'}


def build():
    spec = design()
    env, lookup = environments(), names()
    stage60 = read(STAGE60_FIT)
    result = {'stage': 67, 'penalty': 0.0, 'bound': BOUND, 'folds': {}}
    for year in YEARS:
        earlier = spec['folds'][str(year)]
        record = {'targetYear': year, 'trainingYears': earlier, 'free': stage60['folds'][str(year)]['multipliers']['free'],
                  'trainingFlagged': {arm: int(sum(indicator(env[y]['ids'], y, kind, lookup).sum() for y in earlier))
                                      for arm, kind in FLAG_SETS.items()}}
        for arm, kind in FLAG_SETS.items():
            record[arm] = fit_two_group(training(env, earlier, kind, lookup)) if earlier else control_fit()
        record['twogroup_exc1'] = fit_exc1(training(env, earlier, 'primary', lookup)) if earlier else control_fit()
        result['folds'][str(year)] = record
    result['descriptive2026Refit'] = {'trainingYears': list(YEARS), 'scored': False,
                                      **{arm: fit_two_group(training(env, YEARS, kind, lookup)) for arm, kind in FLAG_SETS.items()},
                                      'twogroup_exc1': fit_exc1(training(env, YEARS, 'primary', lookup)),
                                      'stage60Free2026Refit': stage60['descriptive2026Refit']['fit']['multiplier']}
    return result


def main():
    args = arguments()
    verify()
    save('fit.json', build(), args.check, tolerance=1e-6)
    print('Stage67 fits ' + ('reproduced' if args.check else 'written'))


if __name__ == '__main__':
    main()
