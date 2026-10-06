"""Stage60 free arm: earlier-trained penalty-free constant seat-balance multiplier, plus the arm multiplier table."""
import numpy as np
from scipy.optimize import minimize
from scripts.balance_scale.data import environments, centers
from scripts.balance_scale.fit import BOUND, central_gradient, objective, projected, solve, training_set
from .common import PREFIX, STAGE48_FIT, read, save, verify, arguments, design, YEARS

FREE = [True, False, False]


def fit_free(training):
    """Penalty-free constant `a` (b_R = b_T = 0) with the Stage48 starts, bound and independent checks."""
    runs, best = solve(training, FREE, penalised=False)
    theta = np.array(runs[best]['theta'])
    value, gradient = objective(theta, training, penalised=False)
    mask = np.array(FREE)
    powell = minimize(lambda t: objective(np.where(mask, t, 0.), training, penalised=False)[0], np.array(runs[best]['start']),
                      method='Powell', bounds=[(-BOUND, BOUND)] * 3, options={'xtol': 1e-10, 'ftol': 1e-10, 'maxiter': 2000})
    powell_theta = np.where(mask, powell.x, 0.)
    return {'a': float(theta[0]), 'multiplier': float(np.exp(theta[0])), 'objective': value, 'gradient': gradient.tolist(),
            'projectedGradientMax': float(np.max(np.abs(projected(theta, gradient, mask)))),
            'centralDifferenceGradientMaxDifference': float(np.max(np.abs(central_gradient(theta, training, penalised=False) - gradient))),
            'starts': runs, 'chosenStart': best, 'boundContact': bool(abs(abs(theta[0]) - BOUND) < 1e-6),
            'powell': {'a': float(powell_theta[0]), 'objective': float(powell.fun), 'objectiveDifference': abs(float(powell.fun) - value),
                       'maximumParameterDifference': float(np.max(np.abs(powell_theta - theta)))}}


def build():
    spec = design()
    env = environments()
    stage48 = read(STAGE48_FIT)
    result = {'stage': 60, 'ridge': 0.0, 'bound': BOUND, 'folds': {}}
    for year in YEARS:
        earlier = spec['folds'][str(year)]
        record = {'targetYear': year, 'trainingYears': earlier, 'trainingSeats': int(sum(len(env[y]['p']) for y in earlier))}
        if earlier:
            record['free'] = fit_free(training_set(env, earlier, centers(env, earlier)))
            record['stage48DescriptiveUnpenalisedA'] = stage48['folds'][str(year)]['unpenalisedConstant']['a']
            record['stage48PenalisedA'] = stage48['folds'][str(year)]['constant']['theta'][0]
            free_multiplier, penalised = record['free']['multiplier'], float(np.exp(record['stage48PenalisedA']))
        else:
            record['free'] = {'a': 0.0, 'multiplier': 1.0, 'status': 'no earlier candidate residual: control'}
            free_multiplier, penalised = 1.0, 1.0
        record['multipliers'] = {name: (1.0 if arm['role'] == 'control' else arm['multiplier'] if isinstance(arm['multiplier'], float)
                                        else free_multiplier if name == 'free' else penalised)
                                 for name, arm in spec['arms'].items()}
        result['folds'][str(year)] = record
    everything = list(YEARS)
    result['descriptive2026Refit'] = {'trainingYears': everything, 'scored': False,
                                      'fit': fit_free(training_set(env, everything, centers(env, everything))),
                                      'meaning': 'the penalty-free constant the free arm would take for the 2026 forecast; reported only'}
    return result


def main():
    args = arguments()
    verify()
    save('fit.json', build(), args.check, tolerance=1e-6)
    print('Stage60 free-arm multipliers fitted' if not args.check else 'Stage60 fits reproduced')


if __name__ == '__main__':
    main()
