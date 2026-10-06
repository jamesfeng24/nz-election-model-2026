"""Stage48 balance-scale comparison: numerics, fit, frozen decision rule and sealed outputs."""
import json
import unittest
from pathlib import Path
import numpy as np
from scipy.special import expit
from scripts.balance_scale import fit as F, decision as D, summary as S
from scripts.balance_scale.common import ROOT, PREFIX, design, equivalent, RESTRICTIONS
from scripts.balance_scale.data import centered, centers

NODES, WEIGHTS = np.polynomial.hermite_e.hermegauss(161)
WEIGHTS = WEIGHTS / np.sqrt(2 * np.pi)


def synthetic(n, truth, seed, shared=0.12, seat=0.3, features=True, p_low=.3, p_high=.7):
    rng = np.random.default_rng(seed)
    p = rng.uniform(p_low, p_high, n)
    x = rng.uniform(0, 1, (n, 2)) if features else np.zeros((n, 2))
    sigma = seat * np.exp(np.column_stack((np.ones(n), x - .5)) @ np.asarray(truth))
    total = np.sqrt(shared ** 2 + sigma ** 2)
    loc, _ = F.location(p, total)
    v = loc + shared * rng.standard_normal() + sigma * rng.standard_normal(n)
    return {'p': p, 'v': v, 'features': x - .5, 'seat': seat, 'shared': shared}


class Numerics(unittest.TestCase):
    def test_location_preserves_mean_and_derivative(self):
        p = np.array([.05, .3, .5, .8]); sd = np.array([.1, .35, .5, .2])
        loc, derivative = F.location(p, sd)
        self.assertLess(np.max(np.abs(expit(loc[:, None] + sd[:, None] * NODES) @ WEIGHTS - p)), 1e-12)
        step = 1e-6
        finite = (F.location(p, sd + step)[0] - F.location(p, sd - step)[0]) / (2 * step)
        np.testing.assert_allclose(derivative, finite, atol=1e-7)
        with self.assertRaises(ValueError):
            F.location(np.array([0.]), np.array([.1]))

    def test_objective_matches_dense_likelihood_and_finite_differences(self):
        e = synthetic(9, [-.1, .2, -.2], 3)
        theta = np.array([-.15, .3, .1])
        value, gradient = F.environment_value(theta, **e)
        f = np.column_stack((np.ones(9), e['features']))
        sigma = e['seat'] * np.exp(f @ theta)
        loc, _ = F.location(e['p'], np.sqrt(e['shared'] ** 2 + sigma ** 2))
        cov = np.diag(sigma ** 2) + e['shared'] ** 2
        r = e['v'] - loc
        dense = .5 / 9 * (np.linalg.slogdet(cov)[1] + r @ np.linalg.solve(cov, r))
        self.assertAlmostEqual(value, dense, places=12)
        step = 1e-6
        finite = [(F.environment_value(theta + step * np.eye(3)[i], **e)[0] - F.environment_value(theta - step * np.eye(3)[i], **e)[0]) / (2 * step) for i in range(3)]
        np.testing.assert_allclose(gradient, finite, atol=1e-8)

    def test_fit_recovers_scale_without_penalty_and_ridge_shrinks_it(self):
        training = [synthetic(400, [-.4, 0, 0], s, features=False) for s in (1, 2, 3, 4)]
        free = [True, False, False]
        runs, best = F.solve(training, free, penalised=False)
        shrunk, best_shrunk = F.solve(training, free, penalised=True)
        unpenalised, ridge = runs[best]['theta'][0], shrunk[best_shrunk]['theta'][0]
        self.assertLess(abs(unpenalised + .4), .06)
        self.assertGreater(ridge, unpenalised)
        self.assertLess(ridge, 0)
        self.assertEqual(shrunk[best_shrunk]['theta'][1:], [0., 0.])

    def test_bounds_and_projected_gradient(self):
        theta = np.array([F.BOUND, -F.BOUND, 0.])
        g = np.array([-1., 1., 1.])
        projected = F.projected(theta, g, np.array([True, True, True]))
        np.testing.assert_array_equal(projected, [0., 0., 1.])
        self.assertEqual(F.projected(theta, g, np.array([False, False, False])).tolist(), [0., 0., 0.])

    def test_multiplier_and_centering(self):
        env = {2020: {'xR': np.array([.2, np.nan, .6]), 'xT': np.array([.1, .2, np.nan])}, 2017: {'xR': np.array([.4]), 'xT': np.array([.3])}}
        c = centers(env, [2017, 2020])
        self.assertAlmostEqual(c['R'], np.mean([.4, .4]))
        z = centered(env, 2020, c)
        self.assertEqual(z[1, 0], 0.)
        self.assertEqual(z[2, 1], 0.)
        self.assertAlmostEqual(F.multipliers(np.array([np.log(.9), 0., 0.]), z)[0], .9)
        self.assertEqual(centers(env, []), {'R': 0., 'T': 0.})


def population(delta, interval=0., energy=0., coverage=(.5, .8, .9)):
    return {'majorCRPSPP': 3. + delta, 'energyPP': 6. + energy,
            'majorIntervals': {str(l): {'intervalScorePP': 20. + interval, 'coverage': c} for l, c in zip((50, 80, 90), coverage)}}


def section(delta, folds=(-1, -1, -1), **kw):
    summary = {'fittedFolds': {'control': population(0.), 'constant': population(delta, **kw)}}
    for year, f in zip((2017, 2020, 2023), folds):
        summary[str(year)] = {'control': population(0.), 'constant': population(delta * f / abs(f) * abs(delta) if f else 0.)}
        summary[str(year)]['constant']['majorCRPSPP'] = 3. + f * abs(delta)
    return {'summary': summary}


class DecisionRule(unittest.TestCase):
    rule = design()['decision']

    def check(self, **kw):
        delta = kw.pop('delta')
        c = D.compare(section(delta, **kw), 'constant', 'control', self.rule)
        return D.classify(c, self.rule)

    def test_classification_cases(self):
        self.assertEqual(self.check(delta=-.02), 'IMPROVES')
        self.assertEqual(self.check(delta=-.005), 'NEGLIGIBLE')
        self.assertEqual(self.check(delta=.02), 'WORSE')
        self.assertEqual(self.check(delta=-.02, interval=.1), 'MIXED')
        self.assertEqual(self.check(delta=-.02, energy=.03), 'MIXED')
        self.assertEqual(self.check(delta=-.02, folds=(-1, 1, 1)), 'MIXED')
        self.assertEqual(self.check(delta=-.02, folds=(-1, -1, 1)), 'IMPROVES')
        # coverage moves from 0.9 to 0.80 at the 90% level, well away from nominal.
        self.assertEqual(self.check(delta=-.02, coverage=(.5, .8, .8)), 'MIXED')

    def test_finding_table(self):
        f = D.finding
        self.assertEqual(f('IMPROVES', 'NEGLIGIBLE', 'IMPROVES'), 'constant only')
        self.assertEqual(f('IMPROVES', 'WORSE', 'IMPROVES'), 'constant only')
        self.assertEqual(f('IMPROVES', 'IMPROVES', 'IMPROVES'), 'global scale change and predictable heteroskedasticity')
        self.assertEqual(f('NEGLIGIBLE', 'IMPROVES', 'IMPROVES'), 'conditional only')
        self.assertEqual(f('WORSE', 'IMPROVES', 'NEGLIGIBLE'), 'mixed')
        self.assertEqual(f('NEGLIGIBLE', 'NEGLIGIBLE', 'NEGLIGIBLE'), 'neither')
        self.assertEqual(f('WORSE', 'WORSE', 'WORSE'), 'neither')
        self.assertEqual(f('MIXED', 'IMPROVES', 'IMPROVES'), 'mixed')
        self.assertEqual(f('IMPROVES', 'MIXED', 'IMPROVES'), 'mixed')

    def test_resolution_gate_blocks_improvement(self):
        s = section(-.02)
        s['records'] = {r: [{'year': 2017, 'majorCRPSPrefix': 3. + (-.02 if r == 'constant' else 0.) + (.01 if r == 'constant' else 0.)}] for r in RESTRICTIONS}
        c = D.compare(s, 'constant', 'control', self.rule)
        self.assertFalse(c['resolution']['passed'])
        self.assertEqual(D.classify(c, self.rule), 'MIXED')

    def test_contract_thresholds_are_documented(self):
        text = (ROOT / 'docs/stage48-balance-scale-design.md').read_text()
        rule = design()['decision']
        for needle in (f"{rule['crpsMaterialityPP']}", f"+{rule['energyGuardPP']}", f"{rule['coverageGuardAbsolute']}", f"{rule['resolutionTolerancePP']}", '16,384'):
            self.assertIn(needle, text)
        self.assertIsNone(rule['operationalAdoption'])
        self.assertEqual(design()['restrictions'], list(RESTRICTIONS))


class Summaries(unittest.TestCase):
    def record(self, i, delta=0.):
        interval = lambda w: {'covered': [True, False, True], 'widths': [w, w, 1.], 'scores': [w * 2, w * 2, 3.]}
        return {'id': f's{i}', 'year': 2017, 'groups': ['national', 'labour', 'other'], 'ids': ['a', 'b', 'c'], 'crpsPP': [3 + delta, 4 + delta, 1.],
                'energyPP': 6., 'maePP': 2., 'interval50': interval(5), 'interval80': interval(8), 'interval90': interval(10),
                'ranking': {'predictionTimePair': {'ids': ['a', 'b'], 'crpsPP': 5., 'interval50': interval(5), 'interval80': interval(8), 'interval90': interval(10)}}}

    def test_major_crps_uses_only_national_and_labour_equal_seat(self):
        records = {r: [self.record(i, .1 if r == 'constant' else 0.) for i in range(3)] for r in RESTRICTIONS}
        result = S.by_population(records)
        self.assertAlmostEqual(result['allSeats']['control']['majorCRPSPP'], 3.5)
        self.assertAlmostEqual(result['allSeats']['constant']['majorCRPSPP'], 3.6)
        self.assertEqual(result['allSeats']['control']['majorIntervals']['90']['total'], 6)
        records['constant'] = records['constant'][:2]
        with self.assertRaises(ValueError):
            S.by_population(records)


class SealedOutputs(unittest.TestCase):
    def read(self, name):
        path = ROOT / PREFIX / name
        return json.loads(path.read_text()) if path.exists() else None

    def test_fit_file_is_complete_and_chronological(self):
        fits = self.read('fit.json')
        if fits is None:
            self.skipTest('fit not generated')
        self.assertEqual(sorted(fits['folds']), ['2014', '2017', '2020', '2023'])
        for year, fold in fits['folds'].items():
            self.assertTrue(all(y < int(year) for y in fold['trainingYears']))
            self.assertEqual(len(fold['seatIds']), {'2014': 64, '2017': 64, '2020': 65, '2023': 64}[year])
            for r in RESTRICTIONS:
                self.assertEqual(len(fold['multipliers'][r]), len(fold['seatIds']))
        self.assertEqual(fits['folds']['2014']['multipliers']['conditional'], [1.] * 64)
        for year in ('2017', '2020', '2023'):
            self.assertEqual(fits['folds'][year]['control']['theta'], [0., 0., 0.])
            self.assertEqual(fits['folds'][year]['constant']['theta'][1:], [0., 0.])
            self.assertFalse(any(fits['folds'][year]['conditional']['boundContact']))

    def test_equivalence_tolerance(self):
        self.assertTrue(equivalent({'a': [1.0, 2.0]}, {'a': [1.0 + 1e-12, 2.0]}))
        self.assertFalse(equivalent({'a': 1.0}, {'a': 1.1}))
        self.assertFalse(equivalent({'a': 1.0}, {'a': 1.0, 'b': 2}))
        self.assertTrue(equivalent({'a': 1.0}, {'a': 1.0 + 5e-7}, tolerance=1e-6))


if __name__ == '__main__':
    unittest.main()
